from __future__ import annotations

import hashlib
import json
import re
from typing import Any

from app.services import nrc_aps_deterministic_insight_artifact_contract as insight_contract


APS_DETERMINISTIC_CHALLENGE_ARTIFACT_SCHEMA_ID = "aps.deterministic_challenge_artifact.v1"
APS_DETERMINISTIC_CHALLENGE_ARTIFACT_FAILURE_SCHEMA_ID = "aps.deterministic_challenge_artifact_failure.v1"
APS_DETERMINISTIC_CHALLENGE_ARTIFACT_GATE_SCHEMA_ID = "aps.deterministic_challenge_artifact_gate.v1"
APS_DETERMINISTIC_CHALLENGE_ARTIFACT_SCHEMA_VERSION = 1

APS_DETERMINISTIC_CHALLENGE_RULESET_CONTRACT_ID = "aps_deterministic_challenge_ruleset_v1"
APS_DETERMINISTIC_CHALLENGE_RULESET_ID = "single_insight_challenge_checks"
APS_DETERMINISTIC_CHALLENGE_RULESET_VERSION = 1
APS_DETERMINISTIC_CHALLENGE_MODE = "deterministic_checks_only"
APS_DETERMINISTIC_CHALLENGE_ARTIFACT_ID_TOKEN_LEN = insight_contract.APS_DETERMINISTIC_INSIGHT_ARTIFACT_ID_TOKEN_LEN

APS_RUNTIME_FAILURE_INVALID_REQUEST = "invalid_request"
APS_RUNTIME_FAILURE_SOURCE_INSIGHT_ARTIFACT_NOT_FOUND = "source_insight_artifact_not_found"
APS_RUNTIME_FAILURE_SOURCE_INSIGHT_ARTIFACT_INVALID = "source_insight_artifact_invalid"
APS_RUNTIME_FAILURE_SOURCE_INSIGHT_ARTIFACT_CONFLICT = "source_insight_artifact_conflict"
APS_RUNTIME_FAILURE_ARTIFACT_NOT_FOUND = "challenge_artifact_not_found"
APS_RUNTIME_FAILURE_ARTIFACT_INVALID = "challenge_artifact_invalid"
APS_RUNTIME_FAILURE_CONFLICT = "challenge_artifact_conflict"
APS_RUNTIME_FAILURE_WRITE_FAILED = "challenge_artifact_write_failed"
APS_RUNTIME_FAILURE_INTERNAL = "internal_challenge_artifact_error"

APS_GATE_FAILURE_MISSING_REF = "missing_deterministic_challenge_artifact_ref"
APS_GATE_FAILURE_UNRESOLVABLE_REF = "unresolvable_deterministic_challenge_artifact_ref"
APS_GATE_FAILURE_ARTIFACT_SCHEMA = "deterministic_challenge_artifact_schema_mismatch"
APS_GATE_FAILURE_FAILURE_SCHEMA = "deterministic_challenge_artifact_failure_schema_mismatch"
APS_GATE_FAILURE_RULESET = "ruleset_mismatch"
APS_GATE_FAILURE_CHALLENGE_MODE = "challenge_mode_mismatch"
APS_GATE_FAILURE_SOURCE_INSIGHT_REF = "source_insight_ref_mismatch"
APS_GATE_FAILURE_SOURCE_INSIGHT_SUMMARY = "source_insight_summary_mismatch"
APS_GATE_FAILURE_CHALLENGES = "challenges_mismatch"
APS_GATE_FAILURE_CHALLENGE_COUNTS = "challenge_counts_mismatch"
APS_GATE_FAILURE_DISPOSITION_COUNTS = "disposition_counts_mismatch"
APS_GATE_FAILURE_TOTAL_CHALLENGES = "total_challenges_mismatch"
APS_GATE_FAILURE_CHECKSUM = "checksum_mismatch"
APS_GATE_FAILURE_DERIVATION_DRIFT = "deterministic_challenge_artifact_derivation_drift"

APS_CHALLENGE_CATEGORY_COVERAGE = "coverage"
APS_CHALLENGE_CATEGORY_INTERPRETATION = "interpretation"
APS_CHALLENGE_CATEGORY_QUALIFICATION = "qualification"

APS_CHALLENGE_SEVERITY_INFO = "info"
APS_CHALLENGE_SEVERITY_WARNING = "warning"
APS_CHALLENGE_SEVERITY_CRITICAL = "critical"
APS_CHALLENGE_SEVERITIES = (
    APS_CHALLENGE_SEVERITY_INFO,
    APS_CHALLENGE_SEVERITY_WARNING,
    APS_CHALLENGE_SEVERITY_CRITICAL,
)

APS_CHALLENGE_DISPOSITION_BLOCK = "block"
APS_CHALLENGE_DISPOSITION_REVIEW = "review"
APS_CHALLENGE_DISPOSITION_ACKNOWLEDGE = "acknowledge"
APS_CHALLENGE_DISPOSITIONS = (
    APS_CHALLENGE_DISPOSITION_BLOCK,
    APS_CHALLENGE_DISPOSITION_REVIEW,
    APS_CHALLENGE_DISPOSITION_ACKNOWLEDGE,
)

APS_CHECK_ID_BLOCKING_COVERAGE_ABSENCE = "blocking_coverage_absence"
APS_CHECK_ID_PARTIAL_COVERAGE_GAP = "partial_coverage_gap"
APS_CHECK_ID_UNRESOLVED_QUESTIONS_PRESENT = "unresolved_questions_present"
APS_CHECK_ID_CONSTRAINTS_PRESENT = "constraints_present"
APS_CHECK_ID_QUALIFICATION_PRESENT = "qualification_present"
APS_CHECK_VERSION_V1 = 1

APS_CHECK_SPECS: tuple[dict[str, Any], ...] = (
    {
        "check_id": APS_CHECK_ID_BLOCKING_COVERAGE_ABSENCE,
        "check_version": APS_CHECK_VERSION_V1,
        "match_rule_id": insight_contract.APS_RULE_ID_DOSSIER_ZERO_FACTS,
        "category": APS_CHALLENGE_CATEGORY_COVERAGE,
        "severity": APS_CHALLENGE_SEVERITY_CRITICAL,
        "disposition": APS_CHALLENGE_DISPOSITION_BLOCK,
        "message": "Insight reports zero factual coverage; downstream use is blocked until coverage exists.",
    },
    {
        "check_id": APS_CHECK_ID_PARTIAL_COVERAGE_GAP,
        "check_version": APS_CHECK_VERSION_V1,
        "match_rule_id": insight_contract.APS_RULE_ID_SOURCE_PACKET_ZERO_FACTS_PARTIAL,
        "category": APS_CHALLENGE_CATEGORY_COVERAGE,
        "severity": APS_CHALLENGE_SEVERITY_WARNING,
        "disposition": APS_CHALLENGE_DISPOSITION_REVIEW,
        "message": "Insight reports partial factual coverage gaps that require review before downstream use.",
    },
    {
        "check_id": APS_CHECK_ID_UNRESOLVED_QUESTIONS_PRESENT,
        "check_version": APS_CHECK_VERSION_V1,
        "match_rule_id": insight_contract.APS_RULE_ID_DOSSIER_UNRESOLVED_QUESTIONS_PRESENT,
        "category": APS_CHALLENGE_CATEGORY_INTERPRETATION,
        "severity": APS_CHALLENGE_SEVERITY_WARNING,
        "disposition": APS_CHALLENGE_DISPOSITION_REVIEW,
        "message": "Insight reports unresolved questions that require explicit downstream review.",
    },
    {
        "check_id": APS_CHECK_ID_CONSTRAINTS_PRESENT,
        "check_version": APS_CHECK_VERSION_V1,
        "match_rule_id": insight_contract.APS_RULE_ID_DOSSIER_CONSTRAINTS_PRESENT,
        "category": APS_CHALLENGE_CATEGORY_INTERPRETATION,
        "severity": APS_CHALLENGE_SEVERITY_WARNING,
        "disposition": APS_CHALLENGE_DISPOSITION_REVIEW,
        "message": "Insight reports operative constraints that require explicit downstream review.",
    },
    {
        "check_id": APS_CHECK_ID_QUALIFICATION_PRESENT,
        "check_version": APS_CHECK_VERSION_V1,
        "match_rule_id": insight_contract.APS_RULE_ID_DOSSIER_CAVEATS_PRESENT,
        "category": APS_CHALLENGE_CATEGORY_QUALIFICATION,
        "severity": APS_CHALLENGE_SEVERITY_INFO,
        "disposition": APS_CHALLENGE_DISPOSITION_ACKNOWLEDGE,
        "message": "Insight reports caveats that must accompany downstream use.",
    },
)


def canonical_json_bytes(payload: dict[str, Any]) -> bytes:
    return json.dumps(payload, sort_keys=True, ensure_ascii=True, separators=(",", ":")).encode("utf-8")


def stable_hash(payload: dict[str, Any]) -> str:
    return hashlib.sha256(canonical_json_bytes(payload)).hexdigest()


def logical_deterministic_challenge_artifact_payload(payload: dict[str, Any]) -> dict[str, Any]:
    clean = dict(payload)
    clean.pop("deterministic_challenge_artifact_checksum", None)
    clean.pop("_deterministic_challenge_artifact_ref", None)
    clean.pop("_persisted", None)
    clean.pop("generated_at_utc", None)
    return clean


def compute_deterministic_challenge_artifact_checksum(payload: dict[str, Any]) -> str:
    return stable_hash(logical_deterministic_challenge_artifact_payload(payload))


def safe_path_token(value: str) -> str:
    raw = str(value or "").strip() or "unknown"
    return re.sub(r"[^A-Za-z0-9._-]+", "_", raw)


def artifact_id_token(value: str) -> str:
    token = safe_path_token(value)
    return token[:APS_DETERMINISTIC_CHALLENGE_ARTIFACT_ID_TOKEN_LEN] or "unknown"


def expected_deterministic_challenge_artifact_file_name(*, scope: str, deterministic_challenge_artifact_id: str) -> str:
    return (
        f"{safe_path_token(scope)}_{artifact_id_token(deterministic_challenge_artifact_id)}"
        "_aps_deterministic_challenge_artifact_v1.json"
    )


def expected_failure_file_name(*, scope: str, deterministic_challenge_artifact_id: str) -> str:
    return (
        f"{safe_path_token(scope)}_{artifact_id_token(deterministic_challenge_artifact_id)}"
        "_aps_deterministic_challenge_artifact_failure_v1.json"
    )


def derive_failure_deterministic_challenge_artifact_id(*, source_locator: str, error_code: str) -> str:
    raw = ":".join(
        [
            APS_DETERMINISTIC_CHALLENGE_ARTIFACT_FAILURE_SCHEMA_ID,
            APS_DETERMINISTIC_CHALLENGE_RULESET_CONTRACT_ID,
            str(source_locator or ""),
            str(error_code or ""),
        ]
    )
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def derive_deterministic_challenge_artifact_id(*, source_deterministic_insight_artifact_id: str) -> str:
    raw = ":".join(
        [
            APS_DETERMINISTIC_CHALLENGE_ARTIFACT_SCHEMA_ID,
            APS_DETERMINISTIC_CHALLENGE_RULESET_CONTRACT_ID,
            APS_DETERMINISTIC_CHALLENGE_RULESET_ID,
            str(APS_DETERMINISTIC_CHALLENGE_RULESET_VERSION),
            APS_DETERMINISTIC_CHALLENGE_MODE,
            str(source_deterministic_insight_artifact_id or ""),
        ]
    )
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def derive_challenge_id(*, deterministic_challenge_artifact_id: str, check_id: str, check_version: int) -> str:
    raw = ":".join(
        [
            APS_DETERMINISTIC_CHALLENGE_ARTIFACT_SCHEMA_ID,
            str(deterministic_challenge_artifact_id or ""),
            str(check_id or ""),
            str(int(check_version or 0)),
        ]
    )
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def normalize_request_payload(payload: dict[str, Any]) -> dict[str, Any]:
    deterministic_insight_artifact_id = str(payload.get("deterministic_insight_artifact_id") or "").strip() or None
    deterministic_insight_artifact_ref = str(payload.get("deterministic_insight_artifact_ref") or "").strip() or None
    if bool(deterministic_insight_artifact_id) == bool(deterministic_insight_artifact_ref):
        raise ValueError(APS_RUNTIME_FAILURE_INVALID_REQUEST)
    return {
        "deterministic_insight_artifact_id": deterministic_insight_artifact_id,
        "deterministic_insight_artifact_ref": deterministic_insight_artifact_ref,
        "persist_challenge_artifact": bool(payload.get("persist_challenge_artifact", False)),
    }


def ruleset_identity_payload() -> dict[str, Any]:
    return {
        "ruleset_contract_id": APS_DETERMINISTIC_CHALLENGE_RULESET_CONTRACT_ID,
        "ruleset_id": APS_DETERMINISTIC_CHALLENGE_RULESET_ID,
        "ruleset_version": APS_DETERMINISTIC_CHALLENGE_RULESET_VERSION,
    }


def source_deterministic_insight_artifact_summary_payload(source_payload: dict[str, Any]) -> dict[str, Any]:
    source_context_dossier = dict(source_payload.get("source_context_dossier") or {})
    finding_counts = dict(source_payload.get("finding_counts") or {})
    return {
        "schema_id": str(source_payload.get("schema_id") or ""),
        "schema_version": int(source_payload.get("schema_version") or 0),
        "deterministic_insight_artifact_id": str(source_payload.get("deterministic_insight_artifact_id") or ""),
        "deterministic_insight_artifact_checksum": str(source_payload.get("deterministic_insight_artifact_checksum") or ""),
        "deterministic_insight_artifact_ref": (
            str(source_payload.get("_deterministic_insight_artifact_ref") or source_payload.get("deterministic_insight_artifact_ref") or "").strip()
            or None
        ),
        "ruleset_contract_id": str(source_payload.get("ruleset_contract_id") or ""),
        "ruleset_id": str(source_payload.get("ruleset_id") or ""),
        "ruleset_version": int(source_payload.get("ruleset_version") or 0),
        "insight_mode": str(source_payload.get("insight_mode") or ""),
        "owner_run_id": str(source_context_dossier.get("owner_run_id") or ""),
        "source_context_dossier_id": str(source_context_dossier.get("context_dossier_id") or ""),
        "source_context_dossier_checksum": str(source_context_dossier.get("context_dossier_checksum") or ""),
        "source_context_dossier_ref": str(source_context_dossier.get("context_dossier_ref") or "") or None,
        "total_findings": int(source_payload.get("total_findings") or 0),
        "finding_counts": {
            severity: int(finding_counts.get(severity, 0) or 0)
            for severity in insight_contract.APS_FINDING_SEVERITIES
        },
    }


def challenge_evaluation_view(source_payload: dict[str, Any]) -> dict[str, Any]:
    findings = [dict(item or {}) for item in list(source_payload.get("findings") or []) if isinstance(item, dict)]
    finding_counts = dict(source_payload.get("finding_counts") or {})
    return {
        "total_findings": int(source_payload.get("total_findings") or 0),
        "finding_counts": {
            severity: int(finding_counts.get(severity, 0) or 0)
            for severity in insight_contract.APS_FINDING_SEVERITIES
        },
        "findings": [
            {
                "finding_id": str(item.get("finding_id") or ""),
                "rule_id": str(item.get("rule_id") or ""),
                "rule_version": int(item.get("rule_version") or 0),
                "category": str(item.get("category") or ""),
                "severity": str(item.get("severity") or ""),
                "matched_source_packet_count": int(item.get("matched_source_packet_count") or 0),
            }
            for item in findings
        ],
    }


def _challenge_counts(challenges: list[dict[str, Any]]) -> dict[str, int]:
    counts = {severity: 0 for severity in APS_CHALLENGE_SEVERITIES}
    for challenge in challenges:
        severity = str(challenge.get("severity") or "")
        if severity in counts:
            counts[severity] = int(counts.get(severity, 0)) + 1
    return counts


def _disposition_counts(challenges: list[dict[str, Any]]) -> dict[str, int]:
    counts = {disposition: 0 for disposition in APS_CHALLENGE_DISPOSITIONS}
    for challenge in challenges:
        disposition = str(challenge.get("disposition") or "")
        if disposition in counts:
            counts[disposition] = int(counts.get(disposition, 0)) + 1
    return counts


def evaluate_challenges(
    *,
    source_deterministic_insight_artifact: dict[str, Any],
    deterministic_challenge_artifact_id: str,
) -> list[dict[str, Any]]:
    rule_input = challenge_evaluation_view(source_deterministic_insight_artifact)
    source_findings = [dict(item or {}) for item in list(rule_input.get("findings") or []) if isinstance(item, dict)]
    ordered_challenges: list[dict[str, Any]] = []
    for check_spec in APS_CHECK_SPECS:
        match_rule_id = str(check_spec.get("match_rule_id") or "")
        matched_rows: list[tuple[int, dict[str, Any]]] = [
            (index, finding)
            for index, finding in enumerate(source_findings)
            if str(finding.get("rule_id") or "") == match_rule_id
        ]
        if not matched_rows:
            continue
        source_finding_ids = [str(finding.get("finding_id") or "") for _index, finding in matched_rows]
        evidence_pointers = [
            {
                "pointer": f"/source_deterministic_insight_artifact/findings/{index}",
                "source_finding_id": str(finding.get("finding_id") or ""),
                "source_rule_id": str(finding.get("rule_id") or ""),
            }
            for index, finding in matched_rows
        ]
        ordered_challenges.append(
            {
                "challenge_id": derive_challenge_id(
                    deterministic_challenge_artifact_id=deterministic_challenge_artifact_id,
                    check_id=str(check_spec.get("check_id") or ""),
                    check_version=int(check_spec.get("check_version") or 0),
                ),
                "check_id": str(check_spec.get("check_id") or ""),
                "check_version": int(check_spec.get("check_version") or 0),
                "category": str(check_spec.get("category") or ""),
                "severity": str(check_spec.get("severity") or ""),
                "disposition": str(check_spec.get("disposition") or ""),
                "matched_finding_count": len(matched_rows),
                "source_finding_ids": source_finding_ids,
                "message": str(check_spec.get("message") or ""),
                "evidence_pointers": evidence_pointers,
            }
        )
    return ordered_challenges


def build_deterministic_challenge_artifact_payload(
    source_deterministic_insight_artifact_payload: dict[str, Any],
    *,
    generated_at_utc: str,
) -> dict[str, Any]:
    source_summary = source_deterministic_insight_artifact_summary_payload(source_deterministic_insight_artifact_payload)
    payload: dict[str, Any] = {
        "schema_id": APS_DETERMINISTIC_CHALLENGE_ARTIFACT_SCHEMA_ID,
        "schema_version": APS_DETERMINISTIC_CHALLENGE_ARTIFACT_SCHEMA_VERSION,
        "generated_at_utc": str(generated_at_utc or ""),
        **ruleset_identity_payload(),
        "challenge_mode": APS_DETERMINISTIC_CHALLENGE_MODE,
        "source_deterministic_insight_artifact": source_summary,
    }
    payload["deterministic_challenge_artifact_id"] = derive_deterministic_challenge_artifact_id(
        source_deterministic_insight_artifact_id=str(source_summary.get("deterministic_insight_artifact_id") or "")
    )
    challenges = evaluate_challenges(
        source_deterministic_insight_artifact=source_deterministic_insight_artifact_payload,
        deterministic_challenge_artifact_id=str(payload.get("deterministic_challenge_artifact_id") or ""),
    )
    payload["challenges"] = challenges
    payload["total_challenges"] = len(challenges)
    payload["challenge_counts"] = _challenge_counts(challenges)
    payload["disposition_counts"] = _disposition_counts(challenges)
    payload["deterministic_challenge_artifact_checksum"] = compute_deterministic_challenge_artifact_checksum(payload)
    return payload
