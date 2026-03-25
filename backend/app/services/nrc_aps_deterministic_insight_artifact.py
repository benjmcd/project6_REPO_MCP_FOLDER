from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from sqlalchemy.orm import Session

from app.core.config import settings
from app.models import ConnectorRun
from app.services import nrc_aps_context_dossier
from app.services import nrc_aps_context_dossier_contract as dossier_contract
from app.services import nrc_aps_deterministic_insight_artifact_contract as contract
from app.services import nrc_aps_safeguards


class DeterministicInsightArtifactError(RuntimeError):
    def __init__(self, code: str, message: str, *, status_code: int = 400) -> None:
        super().__init__(message)
        self.code = str(code or contract.APS_RUNTIME_FAILURE_INTERNAL)
        self.message = str(message or "")
        self.status_code = int(status_code)


def _utc_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _safe_scope_token(value: str) -> str:
    raw = str(value or "").strip() or "unknown"
    return "".join(ch for ch in raw if ch.isalnum() or ch in {"_", "-", "."}) or "unknown"


def _status_for_error_code(code: str) -> int:
    if code in {
        contract.APS_RUNTIME_FAILURE_INVALID_REQUEST,
        contract.APS_RUNTIME_FAILURE_SOURCE_DOSSIER_INVALID,
    }:
        return 422
    if code in {
        contract.APS_RUNTIME_FAILURE_SOURCE_DOSSIER_NOT_FOUND,
        contract.APS_RUNTIME_FAILURE_ARTIFACT_NOT_FOUND,
    }:
        return 404
    if code in {
        contract.APS_RUNTIME_FAILURE_SOURCE_DOSSIER_CONFLICT,
        contract.APS_RUNTIME_FAILURE_CONFLICT,
    }:
        return 409
    if code in {
        contract.APS_RUNTIME_FAILURE_ARTIFACT_INVALID,
        contract.APS_RUNTIME_FAILURE_WRITE_FAILED,
        contract.APS_RUNTIME_FAILURE_INTERNAL,
    }:
        return 500
    return 422


def deterministic_insight_artifact_path(
    *,
    owner_run_id: str,
    deterministic_insight_artifact_id: str,
    reports_dir: str | Path,
) -> Path:
    scope = f"run_{_safe_scope_token(owner_run_id)}"
    return Path(reports_dir) / contract.expected_deterministic_insight_artifact_file_name(
        scope=scope,
        deterministic_insight_artifact_id=deterministic_insight_artifact_id,
    )


def deterministic_insight_failure_artifact_path(
    *,
    owner_run_id: str,
    deterministic_insight_artifact_id: str,
    reports_dir: str | Path,
) -> Path:
    scope = f"run_{_safe_scope_token(owner_run_id)}"
    return Path(reports_dir) / contract.expected_failure_file_name(
        scope=scope,
        deterministic_insight_artifact_id=deterministic_insight_artifact_id,
    )


def _candidate_deterministic_insight_artifacts_by_id(
    *,
    deterministic_insight_artifact_id: str,
    reports_dir: str | Path,
) -> list[Path]:
    pattern = f"*_{contract.artifact_id_token(deterministic_insight_artifact_id)}_aps_deterministic_insight_artifact_v1.json"
    return sorted(Path(reports_dir).glob(pattern), key=lambda path: path.name)


def _resolve_deterministic_insight_artifact_path(
    *,
    deterministic_insight_artifact_id: str | None = None,
    deterministic_insight_artifact_ref: str | Path | None = None,
) -> Path:
    normalized_id = str(deterministic_insight_artifact_id or "").strip()
    normalized_ref = str(deterministic_insight_artifact_ref or "").strip()
    if bool(normalized_id) == bool(normalized_ref):
        raise DeterministicInsightArtifactError(
            contract.APS_RUNTIME_FAILURE_INVALID_REQUEST,
            "exactly one of deterministic_insight_artifact_id or deterministic_insight_artifact_ref is required",
            status_code=400,
        )
    if normalized_ref:
        candidate_path = Path(normalized_ref)
    else:
        candidate_paths = _candidate_deterministic_insight_artifacts_by_id(
            deterministic_insight_artifact_id=normalized_id,
            reports_dir=settings.connector_reports_dir,
        )
        if not candidate_paths:
            raise DeterministicInsightArtifactError(
                contract.APS_RUNTIME_FAILURE_ARTIFACT_NOT_FOUND,
                "deterministic insight artifact not found",
                status_code=404,
            )
        if len(candidate_paths) > 1:
            raise DeterministicInsightArtifactError(
                contract.APS_RUNTIME_FAILURE_CONFLICT,
                "deterministic insight artifact id is ambiguous across run scopes; use deterministic_insight_artifact_ref",
                status_code=409,
            )
        candidate_path = candidate_paths[0]
    if not candidate_path.exists():
        raise DeterministicInsightArtifactError(
            contract.APS_RUNTIME_FAILURE_ARTIFACT_NOT_FOUND,
            "deterministic insight artifact not found",
            status_code=404,
        )
    return candidate_path


def _read_json(path: str | Path | None) -> dict[str, Any]:
    if not path:
        return {}
    target = Path(path)
    if not target.exists():
        return {}
    try:
        payload = json.loads(target.read_text(encoding="utf-8-sig"))
    except (OSError, ValueError):
        return {}
    if not isinstance(payload, dict):
        return {}
    return payload


def _as_required_text(payload: dict[str, Any], field_name: str) -> str:
    value = str(payload.get(field_name) or "").strip()
    if not value:
        raise DeterministicInsightArtifactError(
            contract.APS_RUNTIME_FAILURE_ARTIFACT_INVALID,
            f"{field_name} missing",
            status_code=500,
        )
    return value


def _as_required_non_negative_int(payload: dict[str, Any], field_name: str) -> int:
    value = payload.get(field_name)
    if isinstance(value, bool) or not isinstance(value, int) or int(value) < 0:
        raise DeterministicInsightArtifactError(
            contract.APS_RUNTIME_FAILURE_ARTIFACT_INVALID,
            f"{field_name} invalid",
            status_code=500,
        )
    return int(value)


def _validate_ruleset_identity(payload: dict[str, Any]) -> None:
    expected = contract.ruleset_identity_payload()
    for field_name, expected_value in expected.items():
        if payload.get(field_name) != expected_value:
            raise DeterministicInsightArtifactError(
                contract.APS_RUNTIME_FAILURE_ARTIFACT_INVALID,
                f"{field_name} mismatch",
                status_code=500,
            )


def _validate_source_context_dossier_summary(payload: dict[str, Any]) -> dict[str, Any]:
    if str(payload.get("schema_id") or "") != dossier_contract.APS_CONTEXT_DOSSIER_SCHEMA_ID:
        raise DeterministicInsightArtifactError(contract.APS_RUNTIME_FAILURE_ARTIFACT_INVALID, "source dossier schema mismatch", status_code=500)
    if int(payload.get("schema_version") or 0) != dossier_contract.APS_CONTEXT_DOSSIER_SCHEMA_VERSION:
        raise DeterministicInsightArtifactError(contract.APS_RUNTIME_FAILURE_ARTIFACT_INVALID, "source dossier schema version mismatch", status_code=500)
    if str(payload.get("composition_contract_id") or "") != dossier_contract.APS_CONTEXT_DOSSIER_COMPOSITION_CONTRACT_ID:
        raise DeterministicInsightArtifactError(contract.APS_RUNTIME_FAILURE_ARTIFACT_INVALID, "source dossier composition contract mismatch", status_code=500)
    if str(payload.get("dossier_mode") or "") != dossier_contract.APS_CONTEXT_DOSSIER_MODE:
        raise DeterministicInsightArtifactError(contract.APS_RUNTIME_FAILURE_ARTIFACT_INVALID, "source dossier mode mismatch", status_code=500)
    for field_name in (
        "context_dossier_id",
        "context_dossier_checksum",
        "context_dossier_ref",
        "owner_run_id",
        "projection_contract_id",
        "fact_grammar_contract_id",
        "objective",
        "source_family",
        "ordered_source_packets_sha256",
    ):
        _as_required_text(payload, field_name)

    source_packets = [dict(item or {}) for item in list(payload.get("source_packets") or []) if isinstance(item, dict)]
    source_packet_count = _as_required_non_negative_int(payload, "source_packet_count")
    if source_packet_count != len(source_packets):
        raise DeterministicInsightArtifactError(contract.APS_RUNTIME_FAILURE_ARTIFACT_INVALID, "source packet count mismatch", status_code=500)

    for index, source_packet in enumerate(source_packets, start=1):
        if int(source_packet.get("packet_ordinal") or 0) != index:
            raise DeterministicInsightArtifactError(contract.APS_RUNTIME_FAILURE_ARTIFACT_INVALID, "source packet ordinal mismatch", status_code=500)
        _as_required_text(source_packet, "context_packet_id")
        _as_required_non_negative_int(source_packet, "total_facts")
        _as_required_non_negative_int(source_packet, "total_caveats")
        _as_required_non_negative_int(source_packet, "total_constraints")
        _as_required_non_negative_int(source_packet, "total_unresolved_questions")

    if _as_required_non_negative_int(payload, "total_facts") != sum(int(item.get("total_facts") or 0) for item in source_packets):
        raise DeterministicInsightArtifactError(contract.APS_RUNTIME_FAILURE_ARTIFACT_INVALID, "source dossier total facts mismatch", status_code=500)
    if _as_required_non_negative_int(payload, "total_caveats") != sum(int(item.get("total_caveats") or 0) for item in source_packets):
        raise DeterministicInsightArtifactError(contract.APS_RUNTIME_FAILURE_ARTIFACT_INVALID, "source dossier total caveats mismatch", status_code=500)
    if _as_required_non_negative_int(payload, "total_constraints") != sum(int(item.get("total_constraints") or 0) for item in source_packets):
        raise DeterministicInsightArtifactError(contract.APS_RUNTIME_FAILURE_ARTIFACT_INVALID, "source dossier total constraints mismatch", status_code=500)
    if _as_required_non_negative_int(payload, "total_unresolved_questions") != sum(int(item.get("total_unresolved_questions") or 0) for item in source_packets):
        raise DeterministicInsightArtifactError(contract.APS_RUNTIME_FAILURE_ARTIFACT_INVALID, "source dossier total unresolved questions mismatch", status_code=500)
    return payload


def _validate_finding_payload(payload: dict[str, Any], *, deterministic_insight_artifact_id: str) -> dict[str, Any]:
    finding_id = _as_required_text(payload, "finding_id")
    rule_id = _as_required_text(payload, "rule_id")
    rule_version = _as_required_non_negative_int(payload, "rule_version")
    expected_rule = next((item for item in contract.APS_RULE_SPECS if str(item.get("rule_id") or "") == rule_id), None)
    if expected_rule is None:
        raise DeterministicInsightArtifactError(contract.APS_RUNTIME_FAILURE_ARTIFACT_INVALID, "unknown rule id", status_code=500)
    if rule_version != int(expected_rule.get("rule_version") or 0):
        raise DeterministicInsightArtifactError(contract.APS_RUNTIME_FAILURE_ARTIFACT_INVALID, "rule version mismatch", status_code=500)
    if str(payload.get("category") or "") != str(expected_rule.get("category") or ""):
        raise DeterministicInsightArtifactError(contract.APS_RUNTIME_FAILURE_ARTIFACT_INVALID, "finding category mismatch", status_code=500)
    if str(payload.get("severity") or "") != str(expected_rule.get("severity") or ""):
        raise DeterministicInsightArtifactError(contract.APS_RUNTIME_FAILURE_ARTIFACT_INVALID, "finding severity mismatch", status_code=500)
    expected_finding_id = contract.derive_finding_id(
        deterministic_insight_artifact_id=deterministic_insight_artifact_id,
        rule_id=rule_id,
        rule_version=rule_version,
    )
    if finding_id != expected_finding_id:
        raise DeterministicInsightArtifactError(contract.APS_RUNTIME_FAILURE_ARTIFACT_INVALID, "finding id mismatch", status_code=500)
    _as_required_text(payload, "message")
    _as_required_non_negative_int(payload, "matched_source_packet_count")
    evidence_pointers = [dict(item or {}) for item in list(payload.get("evidence_pointers") or []) if isinstance(item, dict)]
    if not evidence_pointers:
        raise DeterministicInsightArtifactError(contract.APS_RUNTIME_FAILURE_ARTIFACT_INVALID, "evidence pointers missing", status_code=500)
    for evidence_pointer in evidence_pointers:
        _as_required_text(evidence_pointer, "pointer")
        if "packet_ordinal" in evidence_pointer and (
            isinstance(evidence_pointer.get("packet_ordinal"), bool)
            or not isinstance(evidence_pointer.get("packet_ordinal"), int)
            or int(evidence_pointer.get("packet_ordinal") or 0) < 0
        ):
            raise DeterministicInsightArtifactError(contract.APS_RUNTIME_FAILURE_ARTIFACT_INVALID, "evidence packet ordinal invalid", status_code=500)
        if "context_packet_id" in evidence_pointer:
            _as_required_text(evidence_pointer, "context_packet_id")
    return payload

def _validate_failure_payload_schema(payload: dict[str, Any]) -> dict[str, Any]:
    if str(payload.get("schema_id") or "") != contract.APS_DETERMINISTIC_INSIGHT_ARTIFACT_FAILURE_SCHEMA_ID:
        raise DeterministicInsightArtifactError(contract.APS_RUNTIME_FAILURE_ARTIFACT_INVALID, "failure schema mismatch", status_code=500)
    if int(payload.get("schema_version") or 0) != contract.APS_DETERMINISTIC_INSIGHT_ARTIFACT_SCHEMA_VERSION:
        raise DeterministicInsightArtifactError(contract.APS_RUNTIME_FAILURE_ARTIFACT_INVALID, "failure schema version mismatch", status_code=500)
    _validate_ruleset_identity(payload)
    if str(payload.get("insight_mode") or "") != contract.APS_DETERMINISTIC_INSIGHT_MODE:
        raise DeterministicInsightArtifactError(contract.APS_RUNTIME_FAILURE_ARTIFACT_INVALID, "insight mode mismatch", status_code=500)
    _as_required_text(payload, "deterministic_insight_artifact_id")
    _as_required_text(payload, "owner_run_id")
    _as_required_text(payload, "error_code")
    if not isinstance(payload.get("source_request"), dict):
        raise DeterministicInsightArtifactError(contract.APS_RUNTIME_FAILURE_ARTIFACT_INVALID, "source request mismatch", status_code=500)
    if not isinstance(payload.get("source_context_dossier"), dict):
        raise DeterministicInsightArtifactError(contract.APS_RUNTIME_FAILURE_ARTIFACT_INVALID, "source dossier mismatch", status_code=500)
    checksum = str(payload.get("deterministic_insight_artifact_checksum") or "").strip()
    expected_checksum = contract.compute_deterministic_insight_artifact_checksum(payload)
    if not checksum or checksum != expected_checksum:
        raise DeterministicInsightArtifactError(contract.APS_RUNTIME_FAILURE_ARTIFACT_INVALID, "failure checksum mismatch", status_code=500)
    return payload


def _validate_persisted_deterministic_insight_artifact_payload(payload: dict[str, Any]) -> dict[str, Any]:
    if str(payload.get("schema_id") or "") != contract.APS_DETERMINISTIC_INSIGHT_ARTIFACT_SCHEMA_ID:
        raise DeterministicInsightArtifactError(contract.APS_RUNTIME_FAILURE_ARTIFACT_INVALID, "artifact schema mismatch", status_code=500)
    if int(payload.get("schema_version") or 0) != contract.APS_DETERMINISTIC_INSIGHT_ARTIFACT_SCHEMA_VERSION:
        raise DeterministicInsightArtifactError(contract.APS_RUNTIME_FAILURE_ARTIFACT_INVALID, "artifact schema version mismatch", status_code=500)
    _validate_ruleset_identity(payload)
    if str(payload.get("insight_mode") or "") != contract.APS_DETERMINISTIC_INSIGHT_MODE:
        raise DeterministicInsightArtifactError(contract.APS_RUNTIME_FAILURE_ARTIFACT_INVALID, "insight mode mismatch", status_code=500)

    source_context_dossier = _validate_source_context_dossier_summary(dict(payload.get("source_context_dossier") or {}))
    expected_artifact_id = contract.derive_deterministic_insight_artifact_id(
        source_context_dossier_id=str(source_context_dossier.get("context_dossier_id") or "")
    )
    if str(payload.get("deterministic_insight_artifact_id") or "").strip() != expected_artifact_id:
        raise DeterministicInsightArtifactError(contract.APS_RUNTIME_FAILURE_ARTIFACT_INVALID, "artifact id mismatch", status_code=500)

    findings = [dict(item or {}) for item in list(payload.get("findings") or []) if isinstance(item, dict)]
    if _as_required_non_negative_int(payload, "total_findings") != len(findings):
        raise DeterministicInsightArtifactError(contract.APS_RUNTIME_FAILURE_ARTIFACT_INVALID, "total findings mismatch", status_code=500)
    seen_rule_ids: set[str] = set()
    for finding in findings:
        validated_finding = _validate_finding_payload(
            finding,
            deterministic_insight_artifact_id=expected_artifact_id,
        )
        rule_id = str(validated_finding.get("rule_id") or "")
        if rule_id in seen_rule_ids:
            raise DeterministicInsightArtifactError(contract.APS_RUNTIME_FAILURE_ARTIFACT_INVALID, "duplicate rule id", status_code=500)
        seen_rule_ids.add(rule_id)

    expected_payload = contract.build_deterministic_insight_artifact_payload(
        {
            "schema_id": source_context_dossier.get("schema_id"),
            "schema_version": source_context_dossier.get("schema_version"),
            "context_dossier_id": source_context_dossier.get("context_dossier_id"),
            "context_dossier_checksum": source_context_dossier.get("context_dossier_checksum"),
            "_context_dossier_ref": source_context_dossier.get("context_dossier_ref"),
            "composition_contract_id": source_context_dossier.get("composition_contract_id"),
            "dossier_mode": source_context_dossier.get("dossier_mode"),
            "owner_run_id": source_context_dossier.get("owner_run_id"),
            "projection_contract_id": source_context_dossier.get("projection_contract_id"),
            "fact_grammar_contract_id": source_context_dossier.get("fact_grammar_contract_id"),
            "objective": source_context_dossier.get("objective"),
            "source_family": source_context_dossier.get("source_family"),
            "source_packet_count": source_context_dossier.get("source_packet_count"),
            "ordered_source_packets_sha256": source_context_dossier.get("ordered_source_packets_sha256"),
            "total_facts": source_context_dossier.get("total_facts"),
            "total_caveats": source_context_dossier.get("total_caveats"),
            "total_constraints": source_context_dossier.get("total_constraints"),
            "total_unresolved_questions": source_context_dossier.get("total_unresolved_questions"),
            "source_packets": [
                {
                    "packet_ordinal": item.get("packet_ordinal"),
                    "context_packet_id": item.get("context_packet_id"),
                    "total_facts": item.get("total_facts"),
                    "total_caveats": item.get("total_caveats"),
                    "total_constraints": item.get("total_constraints"),
                    "total_unresolved_questions": item.get("total_unresolved_questions"),
                }
                for item in list(source_context_dossier.get("source_packets") or [])
                if isinstance(item, dict)
            ],
        },
        generated_at_utc=str(payload.get("generated_at_utc") or ""),
    )
    actual_counts = {
        severity: int(dict(payload.get("finding_counts") or {}).get(severity, 0) or 0)
        for severity in contract.APS_FINDING_SEVERITIES
    }
    if actual_counts != dict(expected_payload.get("finding_counts") or {}):
        raise DeterministicInsightArtifactError(contract.APS_RUNTIME_FAILURE_ARTIFACT_INVALID, "finding counts mismatch", status_code=500)
    actual_findings = [dict(item or {}) for item in list(payload.get("findings") or []) if isinstance(item, dict)]
    expected_findings = [dict(item or {}) for item in list(expected_payload.get("findings") or []) if isinstance(item, dict)]
    if actual_findings != expected_findings:
        raise DeterministicInsightArtifactError(contract.APS_RUNTIME_FAILURE_ARTIFACT_INVALID, "findings mismatch", status_code=500)

    checksum = str(payload.get("deterministic_insight_artifact_checksum") or "").strip()
    expected_checksum = contract.compute_deterministic_insight_artifact_checksum(payload)
    if not checksum or checksum != expected_checksum:
        raise DeterministicInsightArtifactError(contract.APS_RUNTIME_FAILURE_ARTIFACT_INVALID, "artifact checksum mismatch", status_code=500)
    return payload


def load_persisted_deterministic_insight_artifact(
    *,
    deterministic_insight_artifact_id: str | None = None,
    deterministic_insight_artifact_ref: str | Path | None = None,
) -> tuple[dict[str, Any], Path]:
    candidate_path = _resolve_deterministic_insight_artifact_path(
        deterministic_insight_artifact_id=deterministic_insight_artifact_id,
        deterministic_insight_artifact_ref=deterministic_insight_artifact_ref,
    )
    payload = _read_json(candidate_path)
    if not payload:
        raise DeterministicInsightArtifactError(
            contract.APS_RUNTIME_FAILURE_ARTIFACT_INVALID,
            "deterministic insight artifact unreadable",
            status_code=500,
        )
    validated_payload = _validate_persisted_deterministic_insight_artifact_payload(payload)
    validated_payload["_deterministic_insight_artifact_ref"] = str(candidate_path)
    validated_payload["_persisted"] = True
    return validated_payload, candidate_path


def _conflict_error(message: str, *, inner_code: str | None = None) -> DeterministicInsightArtifactError:
    details = f"{message}: {inner_code}" if inner_code else message
    return DeterministicInsightArtifactError(contract.APS_RUNTIME_FAILURE_CONFLICT, details, status_code=409)


def _persist_or_validate_deterministic_insight_artifact(
    *,
    artifact_path: Path,
    payload: dict[str, Any],
) -> tuple[dict[str, Any], str]:
    if artifact_path.exists():
        try:
            existing_payload, existing_path = load_persisted_deterministic_insight_artifact(
                deterministic_insight_artifact_ref=artifact_path
            )
        except DeterministicInsightArtifactError as exc:
            raise _conflict_error(
                "existing persisted deterministic insight artifact conflicts with derived artifact",
                inner_code=contract.APS_RUNTIME_FAILURE_ARTIFACT_INVALID,
            ) from exc
        if str(existing_payload.get("deterministic_insight_artifact_id") or "").strip() != str(payload.get("deterministic_insight_artifact_id") or "").strip():
            raise _conflict_error("existing persisted deterministic insight artifact id conflicts with derived artifact")
        if str(existing_payload.get("deterministic_insight_artifact_checksum") or "").strip() != str(payload.get("deterministic_insight_artifact_checksum") or "").strip():
            raise _conflict_error("existing persisted deterministic insight artifact checksum conflicts with derived artifact")
        if contract.logical_deterministic_insight_artifact_payload(existing_payload) != contract.logical_deterministic_insight_artifact_payload(payload):
            raise _conflict_error("existing persisted deterministic insight artifact body conflicts with derived artifact")
        return existing_payload, str(existing_path)

    artifact_ref = nrc_aps_safeguards.write_json_atomic(artifact_path, payload)
    validated_payload, _validated_path = load_persisted_deterministic_insight_artifact(
        deterministic_insight_artifact_ref=artifact_ref
    )
    return validated_payload, artifact_ref


def _append_deterministic_insight_artifact_summary(existing: list[dict[str, Any]] | None, entry: dict[str, Any]) -> list[dict[str, Any]]:
    summaries = [dict(item or {}) for item in (existing or []) if isinstance(item, dict)]
    incoming_artifact_id = str(entry.get("deterministic_insight_artifact_id") or "").strip()
    incoming_ref = str(entry.get("ref") or "").strip()
    kept: list[dict[str, Any]] = []
    replaced = False
    for item in summaries:
        same_artifact_id = str(item.get("deterministic_insight_artifact_id") or "").strip() == incoming_artifact_id
        same_ref = incoming_ref and str(item.get("ref") or "").strip() == incoming_ref
        if same_artifact_id or same_ref:
            if not replaced:
                kept.append(dict(entry))
                replaced = True
            continue
        kept.append(item)
    if not replaced:
        kept.append(dict(entry))
    kept.sort(key=lambda item: (str(item.get("deterministic_insight_artifact_id") or ""), str(item.get("ref") or "")))
    return kept

def _candidate_run(db: Session, run_id: str | None) -> ConnectorRun | None:
    normalized_run_id = str(run_id or "").strip()
    if not normalized_run_id:
        return None
    return db.get(ConnectorRun, normalized_run_id)


def _response_payload(payload: dict[str, Any]) -> dict[str, Any]:
    return {
        "generated_at_utc": str(payload.get("generated_at_utc") or ""),
        "schema_id": str(payload.get("schema_id") or contract.APS_DETERMINISTIC_INSIGHT_ARTIFACT_SCHEMA_ID),
        "schema_version": int(payload.get("schema_version") or contract.APS_DETERMINISTIC_INSIGHT_ARTIFACT_SCHEMA_VERSION),
        "deterministic_insight_artifact_id": str(payload.get("deterministic_insight_artifact_id") or ""),
        "deterministic_insight_artifact_checksum": str(payload.get("deterministic_insight_artifact_checksum") or ""),
        "deterministic_insight_artifact_ref": str(payload.get("_deterministic_insight_artifact_ref") or "") or None,
        "ruleset_contract_id": str(payload.get("ruleset_contract_id") or contract.APS_DETERMINISTIC_INSIGHT_RULESET_CONTRACT_ID),
        "ruleset_id": str(payload.get("ruleset_id") or contract.APS_DETERMINISTIC_INSIGHT_RULESET_ID),
        "ruleset_version": int(payload.get("ruleset_version") or contract.APS_DETERMINISTIC_INSIGHT_RULESET_VERSION),
        "insight_mode": str(payload.get("insight_mode") or contract.APS_DETERMINISTIC_INSIGHT_MODE),
        "source_context_dossier": dict(payload.get("source_context_dossier") or {}),
        "total_findings": int(payload.get("total_findings") or 0),
        "finding_counts": {
            severity: int(dict(payload.get("finding_counts") or {}).get(severity, 0) or 0)
            for severity in contract.APS_FINDING_SEVERITIES
        },
        "findings": [dict(item or {}) for item in list(payload.get("findings") or []) if isinstance(item, dict)],
        "persisted": bool(payload.get("_persisted", False)),
    }


def _source_dossier_error(exc: nrc_aps_context_dossier.ContextDossierError) -> DeterministicInsightArtifactError:
    if int(exc.status_code) == 404:
        code = contract.APS_RUNTIME_FAILURE_SOURCE_DOSSIER_NOT_FOUND
    elif int(exc.status_code) == 409:
        code = contract.APS_RUNTIME_FAILURE_SOURCE_DOSSIER_CONFLICT
    else:
        code = contract.APS_RUNTIME_FAILURE_SOURCE_DOSSIER_INVALID
    return DeterministicInsightArtifactError(code, str(exc.message), status_code=_status_for_error_code(code))


def _resolve_source_context_dossier_payload(
    normalized_request: dict[str, Any],
) -> tuple[dict[str, Any], Path]:
    try:
        return nrc_aps_context_dossier.load_persisted_context_dossier_artifact(
            context_dossier_id=normalized_request.get("context_dossier_id"),
            context_dossier_ref=normalized_request.get("context_dossier_ref"),
        )
    except nrc_aps_context_dossier.ContextDossierError as exc:
        raise _source_dossier_error(exc) from exc


def _failure_source_locator(normalized_request: dict[str, Any]) -> str:
    return str(normalized_request.get("context_dossier_id") or normalized_request.get("context_dossier_ref") or "unknown")


def _persist_failure_artifact(
    db: Session,
    *,
    run: ConnectorRun | None,
    owner_run_id: str | None,
    normalized_request: dict[str, Any],
    source_payload: dict[str, Any] | None,
    error_code: str,
    error_message: str,
) -> str | None:
    effective_owner_run_id = str(owner_run_id or getattr(run, "connector_run_id", "") or "").strip()
    if not effective_owner_run_id:
        return None
    failure_artifact_id = contract.derive_failure_deterministic_insight_artifact_id(
        source_locator=_failure_source_locator(normalized_request),
        error_code=error_code,
    )
    source_summary = {
        "context_dossier_id": None,
        "context_dossier_checksum": None,
        "context_dossier_ref": None,
    }
    if isinstance(source_payload, dict) and source_payload:
        source_summary = {
            "context_dossier_id": str(source_payload.get("context_dossier_id") or "").strip() or None,
            "context_dossier_checksum": str(source_payload.get("context_dossier_checksum") or "").strip() or None,
            "context_dossier_ref": str(source_payload.get("_context_dossier_ref") or source_payload.get("context_dossier_ref") or "").strip() or None,
        }
    failure_payload: dict[str, Any] = {
        "schema_id": contract.APS_DETERMINISTIC_INSIGHT_ARTIFACT_FAILURE_SCHEMA_ID,
        "schema_version": contract.APS_DETERMINISTIC_INSIGHT_ARTIFACT_SCHEMA_VERSION,
        "generated_at_utc": _utc_iso(),
        "deterministic_insight_artifact_id": failure_artifact_id,
        **contract.ruleset_identity_payload(),
        "insight_mode": contract.APS_DETERMINISTIC_INSIGHT_MODE,
        "owner_run_id": effective_owner_run_id,
        "source_request": {
            "context_dossier_id": normalized_request.get("context_dossier_id"),
            "context_dossier_ref": normalized_request.get("context_dossier_ref"),
            "persist_insight_artifact": bool(normalized_request.get("persist_insight_artifact", False)),
        },
        "source_context_dossier": source_summary,
        "error_code": str(error_code or contract.APS_RUNTIME_FAILURE_INTERNAL),
        "error_message": str(error_message or ""),
    }
    failure_payload["deterministic_insight_artifact_checksum"] = contract.compute_deterministic_insight_artifact_checksum(
        failure_payload
    )
    failure_path = deterministic_insight_failure_artifact_path(
        owner_run_id=effective_owner_run_id,
        deterministic_insight_artifact_id=failure_artifact_id,
        reports_dir=settings.connector_reports_dir,
    )
    failure_ref = nrc_aps_safeguards.write_json_atomic(failure_path, failure_payload)
    if run is None:
        return failure_ref
    existing_refs = dict((run.query_plan_json or {}).get("aps_deterministic_insight_artifact_report_refs") or {})
    failure_refs = [
        str(item).strip()
        for item in list(existing_refs.get("aps_deterministic_insight_artifact_failures") or [])
        if str(item).strip()
    ]
    if failure_ref not in failure_refs:
        failure_refs.append(failure_ref)
    run.query_plan_json = {
        **(run.query_plan_json or {}),
        "aps_deterministic_insight_artifact_report_refs": {
            "aps_deterministic_insight_artifacts": [
                str(item).strip()
                for item in list(existing_refs.get("aps_deterministic_insight_artifacts") or [])
                if str(item).strip()
            ],
            "aps_deterministic_insight_artifact_failures": failure_refs,
        },
    }
    db.commit()
    return failure_ref

def assemble_deterministic_insight_artifact(db: Session, *, request_payload: dict[str, Any]) -> dict[str, Any]:
    try:
        normalized_request = contract.normalize_request_payload(request_payload)
    except ValueError as exc:
        code = str(exc) or contract.APS_RUNTIME_FAILURE_INVALID_REQUEST
        raise DeterministicInsightArtifactError(
            code,
            f"invalid request: {code}",
            status_code=_status_for_error_code(code),
        ) from None

    persist_artifact = bool(normalized_request.get("persist_insight_artifact", False))
    source_payload: dict[str, Any] | None = None
    run: ConnectorRun | None = None
    owner_run_id: str | None = None
    try:
        source_payload, _source_path = _resolve_source_context_dossier_payload(normalized_request)
        source_summary = contract.source_context_dossier_summary_payload(source_payload)
        owner_run_id = str(source_summary.get("owner_run_id") or "").strip() or None
        run = _candidate_run(db, owner_run_id)

        artifact_payload = contract.build_deterministic_insight_artifact_payload(
            source_payload,
            generated_at_utc=_utc_iso(),
        )

        if persist_artifact:
            artifact_path = deterministic_insight_artifact_path(
                owner_run_id=str(owner_run_id or ""),
                deterministic_insight_artifact_id=str(artifact_payload.get("deterministic_insight_artifact_id") or ""),
                reports_dir=settings.connector_reports_dir,
            )
            artifact_payload, artifact_ref = _persist_or_validate_deterministic_insight_artifact(
                artifact_path=artifact_path,
                payload=artifact_payload,
            )
            if run is not None:
                existing_refs = dict((run.query_plan_json or {}).get("aps_deterministic_insight_artifact_report_refs") or {})
                artifact_refs = [
                    str(item).strip()
                    for item in list(existing_refs.get("aps_deterministic_insight_artifacts") or [])
                    if str(item).strip()
                ]
                if artifact_ref not in artifact_refs:
                    artifact_refs.append(artifact_ref)
                failure_refs = [
                    str(item).strip()
                    for item in list(existing_refs.get("aps_deterministic_insight_artifact_failures") or [])
                    if str(item).strip()
                ]
                source_context_dossier = dict(artifact_payload.get("source_context_dossier") or {})
                summaries = _append_deterministic_insight_artifact_summary(
                    (run.query_plan_json or {}).get("aps_deterministic_insight_artifact_summaries"),
                    {
                        "deterministic_insight_artifact_id": str(artifact_payload.get("deterministic_insight_artifact_id") or ""),
                        "deterministic_insight_artifact_checksum": str(artifact_payload.get("deterministic_insight_artifact_checksum") or ""),
                        "ruleset_id": str(artifact_payload.get("ruleset_id") or ""),
                        "ruleset_version": int(artifact_payload.get("ruleset_version") or 0),
                        "source_context_dossier_id": str(source_context_dossier.get("context_dossier_id") or ""),
                        "source_context_dossier_checksum": str(source_context_dossier.get("context_dossier_checksum") or ""),
                        "owner_run_id": str(source_context_dossier.get("owner_run_id") or ""),
                        "total_findings": int(artifact_payload.get("total_findings") or 0),
                        "finding_counts": {
                            severity: int(dict(artifact_payload.get("finding_counts") or {}).get(severity, 0) or 0)
                            for severity in contract.APS_FINDING_SEVERITIES
                        },
                        "ref": artifact_ref,
                    },
                )
                run.query_plan_json = {
                    **(run.query_plan_json or {}),
                    "aps_deterministic_insight_artifact_report_refs": {
                        "aps_deterministic_insight_artifacts": artifact_refs,
                        "aps_deterministic_insight_artifact_failures": failure_refs,
                    },
                    "aps_deterministic_insight_artifact_summaries": summaries,
                }
                db.commit()
            artifact_payload["_deterministic_insight_artifact_ref"] = artifact_ref
            artifact_payload["_persisted"] = True
        else:
            artifact_payload["_deterministic_insight_artifact_ref"] = None
            artifact_payload["_persisted"] = False
        return _response_payload(artifact_payload)
    except DeterministicInsightArtifactError as exc:
        if persist_artifact:
            _persist_failure_artifact(
                db,
                run=run,
                owner_run_id=owner_run_id,
                normalized_request=normalized_request,
                source_payload=source_payload,
                error_code=exc.code,
                error_message=exc.message,
            )
        raise
    except Exception as exc:  # noqa: BLE001
        if persist_artifact:
            _persist_failure_artifact(
                db,
                run=run,
                owner_run_id=owner_run_id,
                normalized_request=normalized_request,
                source_payload=source_payload,
                error_code=contract.APS_RUNTIME_FAILURE_INTERNAL,
                error_message=str(exc),
            )
        raise DeterministicInsightArtifactError(
            contract.APS_RUNTIME_FAILURE_INTERNAL,
            str(exc),
            status_code=500,
        ) from exc


def get_persisted_deterministic_insight_artifact(*, deterministic_insight_artifact_id: str) -> dict[str, Any]:
    payload, _candidate_path = load_persisted_deterministic_insight_artifact(
        deterministic_insight_artifact_id=str(deterministic_insight_artifact_id or "").strip()
    )
    return _response_payload(payload)
