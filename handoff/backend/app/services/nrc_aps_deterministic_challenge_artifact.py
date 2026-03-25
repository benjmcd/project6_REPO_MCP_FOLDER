from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from sqlalchemy.orm import Session

from app.core.config import settings
from app.models import ConnectorRun
from app.services import nrc_aps_deterministic_challenge_artifact_contract as contract
from app.services import nrc_aps_deterministic_insight_artifact
from app.services import nrc_aps_deterministic_insight_artifact_contract as insight_contract
from app.services import nrc_aps_safeguards


class DeterministicChallengeArtifactError(RuntimeError):
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
    if code in {contract.APS_RUNTIME_FAILURE_INVALID_REQUEST, contract.APS_RUNTIME_FAILURE_SOURCE_INSIGHT_ARTIFACT_INVALID}:
        return 422
    if code in {contract.APS_RUNTIME_FAILURE_SOURCE_INSIGHT_ARTIFACT_NOT_FOUND, contract.APS_RUNTIME_FAILURE_ARTIFACT_NOT_FOUND}:
        return 404
    if code in {contract.APS_RUNTIME_FAILURE_SOURCE_INSIGHT_ARTIFACT_CONFLICT, contract.APS_RUNTIME_FAILURE_CONFLICT}:
        return 409
    if code in {contract.APS_RUNTIME_FAILURE_ARTIFACT_INVALID, contract.APS_RUNTIME_FAILURE_WRITE_FAILED, contract.APS_RUNTIME_FAILURE_INTERNAL}:
        return 500
    return 422


def deterministic_challenge_artifact_path(*, owner_run_id: str, deterministic_challenge_artifact_id: str, reports_dir: str | Path) -> Path:
    scope = f"run_{_safe_scope_token(owner_run_id)}"
    return Path(reports_dir) / contract.expected_deterministic_challenge_artifact_file_name(
        scope=scope,
        deterministic_challenge_artifact_id=deterministic_challenge_artifact_id,
    )


def deterministic_challenge_failure_artifact_path(*, owner_run_id: str, deterministic_challenge_artifact_id: str, reports_dir: str | Path) -> Path:
    scope = f"run_{_safe_scope_token(owner_run_id)}"
    return Path(reports_dir) / contract.expected_failure_file_name(
        scope=scope,
        deterministic_challenge_artifact_id=deterministic_challenge_artifact_id,
    )


def _candidate_deterministic_challenge_artifacts_by_id(*, deterministic_challenge_artifact_id: str, reports_dir: str | Path) -> list[Path]:
    pattern = f"*_{contract.artifact_id_token(deterministic_challenge_artifact_id)}_aps_deterministic_challenge_artifact_v1.json"
    return sorted(Path(reports_dir).glob(pattern), key=lambda path: path.name)


def _resolve_deterministic_challenge_artifact_path(*, deterministic_challenge_artifact_id: str | None = None, deterministic_challenge_artifact_ref: str | Path | None = None) -> Path:
    normalized_id = str(deterministic_challenge_artifact_id or "").strip()
    normalized_ref = str(deterministic_challenge_artifact_ref or "").strip()
    if bool(normalized_id) == bool(normalized_ref):
        raise DeterministicChallengeArtifactError(contract.APS_RUNTIME_FAILURE_INVALID_REQUEST, "exactly one of deterministic_challenge_artifact_id or deterministic_challenge_artifact_ref is required", status_code=400)
    if normalized_ref:
        candidate_path = Path(normalized_ref)
    else:
        candidate_paths = _candidate_deterministic_challenge_artifacts_by_id(
            deterministic_challenge_artifact_id=normalized_id,
            reports_dir=settings.connector_reports_dir,
        )
        if not candidate_paths:
            raise DeterministicChallengeArtifactError(contract.APS_RUNTIME_FAILURE_ARTIFACT_NOT_FOUND, "deterministic challenge artifact not found", status_code=404)
        if len(candidate_paths) > 1:
            raise DeterministicChallengeArtifactError(contract.APS_RUNTIME_FAILURE_CONFLICT, "deterministic challenge artifact id is ambiguous across run scopes; use deterministic_challenge_artifact_ref", status_code=409)
        candidate_path = candidate_paths[0]
    if not candidate_path.exists():
        raise DeterministicChallengeArtifactError(contract.APS_RUNTIME_FAILURE_ARTIFACT_NOT_FOUND, "deterministic challenge artifact not found", status_code=404)
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
    return payload if isinstance(payload, dict) else {}


def _as_required_text(payload: dict[str, Any], field_name: str) -> str:
    value = str(payload.get(field_name) or "").strip()
    if not value:
        raise DeterministicChallengeArtifactError(contract.APS_RUNTIME_FAILURE_ARTIFACT_INVALID, f"{field_name} missing", status_code=500)
    return value


def _as_required_non_negative_int(payload: dict[str, Any], field_name: str) -> int:
    value = payload.get(field_name)
    if isinstance(value, bool) or not isinstance(value, int) or int(value) < 0:
        raise DeterministicChallengeArtifactError(contract.APS_RUNTIME_FAILURE_ARTIFACT_INVALID, f"{field_name} invalid", status_code=500)
    return int(value)


def _validate_ruleset_identity(payload: dict[str, Any]) -> None:
    for field_name, expected_value in contract.ruleset_identity_payload().items():
        if payload.get(field_name) != expected_value:
            raise DeterministicChallengeArtifactError(contract.APS_RUNTIME_FAILURE_ARTIFACT_INVALID, f"{field_name} mismatch", status_code=500)


def _validate_source_deterministic_insight_artifact_summary(payload: dict[str, Any]) -> dict[str, Any]:
    if str(payload.get("schema_id") or "") != insight_contract.APS_DETERMINISTIC_INSIGHT_ARTIFACT_SCHEMA_ID:
        raise DeterministicChallengeArtifactError(contract.APS_RUNTIME_FAILURE_ARTIFACT_INVALID, "source insight schema mismatch", status_code=500)
    if int(payload.get("schema_version") or 0) != insight_contract.APS_DETERMINISTIC_INSIGHT_ARTIFACT_SCHEMA_VERSION:
        raise DeterministicChallengeArtifactError(contract.APS_RUNTIME_FAILURE_ARTIFACT_INVALID, "source insight schema version mismatch", status_code=500)
    for field_name in (
        "deterministic_insight_artifact_id",
        "deterministic_insight_artifact_checksum",
        "deterministic_insight_artifact_ref",
        "ruleset_contract_id",
        "ruleset_id",
        "owner_run_id",
        "source_context_dossier_id",
        "source_context_dossier_checksum",
        "source_context_dossier_ref",
    ):
        _as_required_text(payload, field_name)
    if str(payload.get("ruleset_contract_id") or "") != insight_contract.APS_DETERMINISTIC_INSIGHT_RULESET_CONTRACT_ID:
        raise DeterministicChallengeArtifactError(contract.APS_RUNTIME_FAILURE_ARTIFACT_INVALID, "source insight ruleset contract mismatch", status_code=500)
    if str(payload.get("ruleset_id") or "") != insight_contract.APS_DETERMINISTIC_INSIGHT_RULESET_ID:
        raise DeterministicChallengeArtifactError(contract.APS_RUNTIME_FAILURE_ARTIFACT_INVALID, "source insight ruleset id mismatch", status_code=500)
    if int(payload.get("ruleset_version") or 0) != insight_contract.APS_DETERMINISTIC_INSIGHT_RULESET_VERSION:
        raise DeterministicChallengeArtifactError(contract.APS_RUNTIME_FAILURE_ARTIFACT_INVALID, "source insight ruleset version mismatch", status_code=500)
    if str(payload.get("insight_mode") or "") != insight_contract.APS_DETERMINISTIC_INSIGHT_MODE:
        raise DeterministicChallengeArtifactError(contract.APS_RUNTIME_FAILURE_ARTIFACT_INVALID, "source insight mode mismatch", status_code=500)
    total_findings = _as_required_non_negative_int(payload, "total_findings")
    finding_counts = dict(payload.get("finding_counts") or {})
    if sum(int(finding_counts.get(severity, 0) or 0) for severity in insight_contract.APS_FINDING_SEVERITIES) != total_findings:
        raise DeterministicChallengeArtifactError(contract.APS_RUNTIME_FAILURE_ARTIFACT_INVALID, "source insight total findings mismatch", status_code=500)
    return payload

def _validate_challenge_payload(payload: dict[str, Any], *, deterministic_challenge_artifact_id: str) -> dict[str, Any]:
    challenge_id = _as_required_text(payload, "challenge_id")
    check_id = _as_required_text(payload, "check_id")
    check_version = _as_required_non_negative_int(payload, "check_version")
    expected_check = next((item for item in contract.APS_CHECK_SPECS if str(item.get("check_id") or "") == check_id), None)
    if expected_check is None:
        raise DeterministicChallengeArtifactError(contract.APS_RUNTIME_FAILURE_ARTIFACT_INVALID, "unknown check id", status_code=500)
    if check_version != int(expected_check.get("check_version") or 0):
        raise DeterministicChallengeArtifactError(contract.APS_RUNTIME_FAILURE_ARTIFACT_INVALID, "check version mismatch", status_code=500)
    for field_name in ("category", "severity", "disposition", "message"):
        if str(payload.get(field_name) or "") != str(expected_check.get(field_name) or ""):
            raise DeterministicChallengeArtifactError(contract.APS_RUNTIME_FAILURE_ARTIFACT_INVALID, f"challenge {field_name} mismatch", status_code=500)
    expected_challenge_id = contract.derive_challenge_id(
        deterministic_challenge_artifact_id=deterministic_challenge_artifact_id,
        check_id=check_id,
        check_version=check_version,
    )
    if challenge_id != expected_challenge_id:
        raise DeterministicChallengeArtifactError(contract.APS_RUNTIME_FAILURE_ARTIFACT_INVALID, "challenge id mismatch", status_code=500)
    matched_finding_count = _as_required_non_negative_int(payload, "matched_finding_count")
    source_finding_ids = [str(item or "").strip() for item in list(payload.get("source_finding_ids") or []) if str(item or "").strip()]
    if matched_finding_count != len(source_finding_ids):
        raise DeterministicChallengeArtifactError(contract.APS_RUNTIME_FAILURE_ARTIFACT_INVALID, "matched finding count mismatch", status_code=500)
    evidence_pointers = [dict(item or {}) for item in list(payload.get("evidence_pointers") or []) if isinstance(item, dict)]
    if len(evidence_pointers) != len(source_finding_ids):
        raise DeterministicChallengeArtifactError(contract.APS_RUNTIME_FAILURE_ARTIFACT_INVALID, "evidence pointers mismatch", status_code=500)
    for evidence_pointer in evidence_pointers:
        if not _as_required_text(evidence_pointer, "pointer").startswith("/source_deterministic_insight_artifact/"):
            raise DeterministicChallengeArtifactError(contract.APS_RUNTIME_FAILURE_ARTIFACT_INVALID, "evidence pointer outside source insight boundary", status_code=500)
        if "source_finding_id" in evidence_pointer:
            _as_required_text(evidence_pointer, "source_finding_id")
        if "source_rule_id" in evidence_pointer:
            _as_required_text(evidence_pointer, "source_rule_id")
    return payload


def _validate_failure_payload_schema(payload: dict[str, Any]) -> dict[str, Any]:
    if str(payload.get("schema_id") or "") != contract.APS_DETERMINISTIC_CHALLENGE_ARTIFACT_FAILURE_SCHEMA_ID:
        raise DeterministicChallengeArtifactError(contract.APS_RUNTIME_FAILURE_ARTIFACT_INVALID, "failure schema mismatch", status_code=500)
    if int(payload.get("schema_version") or 0) != contract.APS_DETERMINISTIC_CHALLENGE_ARTIFACT_SCHEMA_VERSION:
        raise DeterministicChallengeArtifactError(contract.APS_RUNTIME_FAILURE_ARTIFACT_INVALID, "failure schema version mismatch", status_code=500)
    _validate_ruleset_identity(payload)
    if str(payload.get("challenge_mode") or "") != contract.APS_DETERMINISTIC_CHALLENGE_MODE:
        raise DeterministicChallengeArtifactError(contract.APS_RUNTIME_FAILURE_ARTIFACT_INVALID, "challenge mode mismatch", status_code=500)
    _as_required_text(payload, "deterministic_challenge_artifact_id")
    _as_required_text(payload, "owner_run_id")
    _as_required_text(payload, "error_code")
    if not isinstance(payload.get("source_request"), dict):
        raise DeterministicChallengeArtifactError(contract.APS_RUNTIME_FAILURE_ARTIFACT_INVALID, "source request mismatch", status_code=500)
    if not isinstance(payload.get("source_deterministic_insight_artifact"), dict):
        raise DeterministicChallengeArtifactError(contract.APS_RUNTIME_FAILURE_ARTIFACT_INVALID, "source insight mismatch", status_code=500)
    checksum = str(payload.get("deterministic_challenge_artifact_checksum") or "").strip()
    if not checksum or checksum != contract.compute_deterministic_challenge_artifact_checksum(payload):
        raise DeterministicChallengeArtifactError(contract.APS_RUNTIME_FAILURE_ARTIFACT_INVALID, "failure checksum mismatch", status_code=500)
    return payload


def _validate_persisted_deterministic_challenge_artifact_payload(payload: dict[str, Any]) -> dict[str, Any]:
    if str(payload.get("schema_id") or "") != contract.APS_DETERMINISTIC_CHALLENGE_ARTIFACT_SCHEMA_ID:
        raise DeterministicChallengeArtifactError(contract.APS_RUNTIME_FAILURE_ARTIFACT_INVALID, "artifact schema mismatch", status_code=500)
    if int(payload.get("schema_version") or 0) != contract.APS_DETERMINISTIC_CHALLENGE_ARTIFACT_SCHEMA_VERSION:
        raise DeterministicChallengeArtifactError(contract.APS_RUNTIME_FAILURE_ARTIFACT_INVALID, "artifact schema version mismatch", status_code=500)
    _validate_ruleset_identity(payload)
    if str(payload.get("challenge_mode") or "") != contract.APS_DETERMINISTIC_CHALLENGE_MODE:
        raise DeterministicChallengeArtifactError(contract.APS_RUNTIME_FAILURE_ARTIFACT_INVALID, "challenge mode mismatch", status_code=500)
    source_summary = _validate_source_deterministic_insight_artifact_summary(dict(payload.get("source_deterministic_insight_artifact") or {}))
    expected_artifact_id = contract.derive_deterministic_challenge_artifact_id(
        source_deterministic_insight_artifact_id=str(source_summary.get("deterministic_insight_artifact_id") or "")
    )
    if str(payload.get("deterministic_challenge_artifact_id") or "").strip() != expected_artifact_id:
        raise DeterministicChallengeArtifactError(contract.APS_RUNTIME_FAILURE_ARTIFACT_INVALID, "artifact id mismatch", status_code=500)
    challenges = [dict(item or {}) for item in list(payload.get("challenges") or []) if isinstance(item, dict)]
    if _as_required_non_negative_int(payload, "total_challenges") != len(challenges):
        raise DeterministicChallengeArtifactError(contract.APS_RUNTIME_FAILURE_ARTIFACT_INVALID, "total challenges mismatch", status_code=500)
    seen_check_ids: set[str] = set()
    for challenge in challenges:
        validated = _validate_challenge_payload(challenge, deterministic_challenge_artifact_id=expected_artifact_id)
        check_id = str(validated.get("check_id") or "")
        if check_id in seen_check_ids:
            raise DeterministicChallengeArtifactError(contract.APS_RUNTIME_FAILURE_ARTIFACT_INVALID, "duplicate check id", status_code=500)
        seen_check_ids.add(check_id)
    expected_challenge_counts = {severity: 0 for severity in contract.APS_CHALLENGE_SEVERITIES}
    expected_disposition_counts = {disposition: 0 for disposition in contract.APS_CHALLENGE_DISPOSITIONS}
    for challenge in challenges:
        expected_challenge_counts[str(challenge.get("severity") or "")] += 1
        expected_disposition_counts[str(challenge.get("disposition") or "")] += 1
    actual_challenge_counts = {severity: int(dict(payload.get("challenge_counts") or {}).get(severity, 0) or 0) for severity in contract.APS_CHALLENGE_SEVERITIES}
    actual_disposition_counts = {disposition: int(dict(payload.get("disposition_counts") or {}).get(disposition, 0) or 0) for disposition in contract.APS_CHALLENGE_DISPOSITIONS}
    if actual_challenge_counts != expected_challenge_counts:
        raise DeterministicChallengeArtifactError(contract.APS_RUNTIME_FAILURE_ARTIFACT_INVALID, "challenge counts mismatch", status_code=500)
    if actual_disposition_counts != expected_disposition_counts:
        raise DeterministicChallengeArtifactError(contract.APS_RUNTIME_FAILURE_ARTIFACT_INVALID, "disposition counts mismatch", status_code=500)
    checksum = str(payload.get("deterministic_challenge_artifact_checksum") or "").strip()
    if not checksum or checksum != contract.compute_deterministic_challenge_artifact_checksum(payload):
        raise DeterministicChallengeArtifactError(contract.APS_RUNTIME_FAILURE_ARTIFACT_INVALID, "artifact checksum mismatch", status_code=500)
    return payload


def load_persisted_deterministic_challenge_artifact(*, deterministic_challenge_artifact_id: str | None = None, deterministic_challenge_artifact_ref: str | Path | None = None) -> tuple[dict[str, Any], Path]:
    candidate_path = _resolve_deterministic_challenge_artifact_path(
        deterministic_challenge_artifact_id=deterministic_challenge_artifact_id,
        deterministic_challenge_artifact_ref=deterministic_challenge_artifact_ref,
    )
    payload = _read_json(candidate_path)
    if not payload:
        raise DeterministicChallengeArtifactError(contract.APS_RUNTIME_FAILURE_ARTIFACT_INVALID, "deterministic challenge artifact unreadable", status_code=500)
    validated_payload = _validate_persisted_deterministic_challenge_artifact_payload(payload)
    validated_payload["_deterministic_challenge_artifact_ref"] = str(candidate_path)
    validated_payload["_persisted"] = True
    return validated_payload, candidate_path


def _conflict_error(message: str, *, inner_code: str | None = None) -> DeterministicChallengeArtifactError:
    details = f"{message}: {inner_code}" if inner_code else message
    return DeterministicChallengeArtifactError(contract.APS_RUNTIME_FAILURE_CONFLICT, details, status_code=409)


def _persist_or_validate_deterministic_challenge_artifact(*, artifact_path: Path, payload: dict[str, Any]) -> tuple[dict[str, Any], str]:
    if artifact_path.exists():
        try:
            existing_payload, existing_path = load_persisted_deterministic_challenge_artifact(deterministic_challenge_artifact_ref=artifact_path)
        except DeterministicChallengeArtifactError as exc:
            raise _conflict_error("existing persisted deterministic challenge artifact conflicts with derived artifact", inner_code=contract.APS_RUNTIME_FAILURE_ARTIFACT_INVALID) from exc
        if str(existing_payload.get("deterministic_challenge_artifact_id") or "").strip() != str(payload.get("deterministic_challenge_artifact_id") or "").strip():
            raise _conflict_error("existing persisted deterministic challenge artifact id conflicts with derived artifact")
        if str(existing_payload.get("deterministic_challenge_artifact_checksum") or "").strip() != str(payload.get("deterministic_challenge_artifact_checksum") or "").strip():
            raise _conflict_error("existing persisted deterministic challenge artifact checksum conflicts with derived artifact")
        if contract.logical_deterministic_challenge_artifact_payload(existing_payload) != contract.logical_deterministic_challenge_artifact_payload(payload):
            raise _conflict_error("existing persisted deterministic challenge artifact body conflicts with derived artifact")
        return existing_payload, str(existing_path)
    artifact_ref = nrc_aps_safeguards.write_json_atomic(artifact_path, payload)
    validated_payload, _validated_path = load_persisted_deterministic_challenge_artifact(deterministic_challenge_artifact_ref=artifact_ref)
    return validated_payload, artifact_ref

def _append_deterministic_challenge_artifact_summary(existing: list[dict[str, Any]] | None, entry: dict[str, Any]) -> list[dict[str, Any]]:
    summaries = [dict(item or {}) for item in (existing or []) if isinstance(item, dict)]
    incoming_artifact_id = str(entry.get("deterministic_challenge_artifact_id") or "").strip()
    incoming_ref = str(entry.get("ref") or "").strip()
    kept: list[dict[str, Any]] = []
    replaced = False
    for item in summaries:
        same_artifact_id = str(item.get("deterministic_challenge_artifact_id") or "").strip() == incoming_artifact_id
        same_ref = incoming_ref and str(item.get("ref") or "").strip() == incoming_ref
        if same_artifact_id or same_ref:
            if not replaced:
                kept.append(dict(entry))
                replaced = True
            continue
        kept.append(item)
    if not replaced:
        kept.append(dict(entry))
    kept.sort(key=lambda item: (str(item.get("deterministic_challenge_artifact_id") or ""), str(item.get("ref") or "")))
    return kept


def _candidate_run(db: Session, run_id: str | None) -> ConnectorRun | None:
    normalized_run_id = str(run_id or "").strip()
    if not normalized_run_id:
        return None
    return db.get(ConnectorRun, normalized_run_id)


def _response_payload(payload: dict[str, Any]) -> dict[str, Any]:
    return {
        "generated_at_utc": str(payload.get("generated_at_utc") or ""),
        "schema_id": str(payload.get("schema_id") or contract.APS_DETERMINISTIC_CHALLENGE_ARTIFACT_SCHEMA_ID),
        "schema_version": int(payload.get("schema_version") or contract.APS_DETERMINISTIC_CHALLENGE_ARTIFACT_SCHEMA_VERSION),
        "deterministic_challenge_artifact_id": str(payload.get("deterministic_challenge_artifact_id") or ""),
        "deterministic_challenge_artifact_checksum": str(payload.get("deterministic_challenge_artifact_checksum") or ""),
        "deterministic_challenge_artifact_ref": str(payload.get("_deterministic_challenge_artifact_ref") or "") or None,
        "ruleset_contract_id": str(payload.get("ruleset_contract_id") or contract.APS_DETERMINISTIC_CHALLENGE_RULESET_CONTRACT_ID),
        "ruleset_id": str(payload.get("ruleset_id") or contract.APS_DETERMINISTIC_CHALLENGE_RULESET_ID),
        "ruleset_version": int(payload.get("ruleset_version") or contract.APS_DETERMINISTIC_CHALLENGE_RULESET_VERSION),
        "challenge_mode": str(payload.get("challenge_mode") or contract.APS_DETERMINISTIC_CHALLENGE_MODE),
        "source_deterministic_insight_artifact": dict(payload.get("source_deterministic_insight_artifact") or {}),
        "total_challenges": int(payload.get("total_challenges") or 0),
        "challenge_counts": {severity: int(dict(payload.get("challenge_counts") or {}).get(severity, 0) or 0) for severity in contract.APS_CHALLENGE_SEVERITIES},
        "disposition_counts": {disposition: int(dict(payload.get("disposition_counts") or {}).get(disposition, 0) or 0) for disposition in contract.APS_CHALLENGE_DISPOSITIONS},
        "challenges": [dict(item or {}) for item in list(payload.get("challenges") or []) if isinstance(item, dict)],
        "persisted": bool(payload.get("_persisted", False)),
    }


def _source_insight_error(exc: nrc_aps_deterministic_insight_artifact.DeterministicInsightArtifactError) -> DeterministicChallengeArtifactError:
    if int(exc.status_code) == 404:
        code = contract.APS_RUNTIME_FAILURE_SOURCE_INSIGHT_ARTIFACT_NOT_FOUND
    elif int(exc.status_code) == 409:
        code = contract.APS_RUNTIME_FAILURE_SOURCE_INSIGHT_ARTIFACT_CONFLICT
    else:
        code = contract.APS_RUNTIME_FAILURE_SOURCE_INSIGHT_ARTIFACT_INVALID
    return DeterministicChallengeArtifactError(code, str(exc.message), status_code=_status_for_error_code(code))


def _resolve_source_deterministic_insight_artifact_payload(normalized_request: dict[str, Any]) -> tuple[dict[str, Any], Path]:
    try:
        return nrc_aps_deterministic_insight_artifact.load_persisted_deterministic_insight_artifact(
            deterministic_insight_artifact_id=normalized_request.get("deterministic_insight_artifact_id"),
            deterministic_insight_artifact_ref=normalized_request.get("deterministic_insight_artifact_ref"),
        )
    except nrc_aps_deterministic_insight_artifact.DeterministicInsightArtifactError as exc:
        raise _source_insight_error(exc) from exc


def _failure_source_locator(normalized_request: dict[str, Any]) -> str:
    return str(normalized_request.get("deterministic_insight_artifact_id") or normalized_request.get("deterministic_insight_artifact_ref") or "unknown")


def _persist_failure_artifact(db: Session, *, run: ConnectorRun | None, owner_run_id: str | None, normalized_request: dict[str, Any], source_payload: dict[str, Any] | None, error_code: str, error_message: str) -> str | None:
    effective_owner_run_id = str(owner_run_id or getattr(run, "connector_run_id", "") or "").strip()
    if not effective_owner_run_id:
        return None
    failure_artifact_id = contract.derive_failure_deterministic_challenge_artifact_id(source_locator=_failure_source_locator(normalized_request), error_code=error_code)
    source_summary = {
        "deterministic_insight_artifact_id": None,
        "deterministic_insight_artifact_checksum": None,
        "deterministic_insight_artifact_ref": None,
    }
    if isinstance(source_payload, dict) and source_payload:
        source_summary = {
            "deterministic_insight_artifact_id": str(source_payload.get("deterministic_insight_artifact_id") or "").strip() or None,
            "deterministic_insight_artifact_checksum": str(source_payload.get("deterministic_insight_artifact_checksum") or "").strip() or None,
            "deterministic_insight_artifact_ref": str(source_payload.get("_deterministic_insight_artifact_ref") or source_payload.get("deterministic_insight_artifact_ref") or "").strip() or None,
        }
    failure_payload: dict[str, Any] = {
        "schema_id": contract.APS_DETERMINISTIC_CHALLENGE_ARTIFACT_FAILURE_SCHEMA_ID,
        "schema_version": contract.APS_DETERMINISTIC_CHALLENGE_ARTIFACT_SCHEMA_VERSION,
        "generated_at_utc": _utc_iso(),
        "deterministic_challenge_artifact_id": failure_artifact_id,
        **contract.ruleset_identity_payload(),
        "challenge_mode": contract.APS_DETERMINISTIC_CHALLENGE_MODE,
        "owner_run_id": effective_owner_run_id,
        "source_request": {
            "deterministic_insight_artifact_id": normalized_request.get("deterministic_insight_artifact_id"),
            "deterministic_insight_artifact_ref": normalized_request.get("deterministic_insight_artifact_ref"),
            "persist_challenge_artifact": bool(normalized_request.get("persist_challenge_artifact", False)),
        },
        "source_deterministic_insight_artifact": source_summary,
        "error_code": str(error_code or contract.APS_RUNTIME_FAILURE_INTERNAL),
        "error_message": str(error_message or ""),
    }
    failure_payload["deterministic_challenge_artifact_checksum"] = contract.compute_deterministic_challenge_artifact_checksum(failure_payload)
    failure_path = deterministic_challenge_failure_artifact_path(owner_run_id=effective_owner_run_id, deterministic_challenge_artifact_id=failure_artifact_id, reports_dir=settings.connector_reports_dir)
    failure_ref = nrc_aps_safeguards.write_json_atomic(failure_path, failure_payload)
    if run is None:
        return failure_ref
    existing_refs = dict((run.query_plan_json or {}).get("aps_deterministic_challenge_artifact_report_refs") or {})
    failure_refs = [str(item).strip() for item in list(existing_refs.get("aps_deterministic_challenge_artifact_failures") or []) if str(item).strip()]
    if failure_ref not in failure_refs:
        failure_refs.append(failure_ref)
    run.query_plan_json = {
        **(run.query_plan_json or {}),
        "aps_deterministic_challenge_artifact_report_refs": {
            "aps_deterministic_challenge_artifacts": [str(item).strip() for item in list(existing_refs.get("aps_deterministic_challenge_artifacts") or []) if str(item).strip()],
            "aps_deterministic_challenge_artifact_failures": failure_refs,
        },
    }
    db.commit()
    return failure_ref


def assemble_deterministic_challenge_artifact(db: Session, *, request_payload: dict[str, Any]) -> dict[str, Any]:
    try:
        normalized_request = contract.normalize_request_payload(request_payload)
    except ValueError as exc:
        code = str(exc) or contract.APS_RUNTIME_FAILURE_INVALID_REQUEST
        raise DeterministicChallengeArtifactError(code, f"invalid request: {code}", status_code=_status_for_error_code(code)) from None
    persist_artifact = bool(normalized_request.get("persist_challenge_artifact", False))
    source_payload: dict[str, Any] | None = None
    run: ConnectorRun | None = None
    owner_run_id: str | None = None
    try:
        source_payload, _source_path = _resolve_source_deterministic_insight_artifact_payload(normalized_request)
        source_summary = contract.source_deterministic_insight_artifact_summary_payload(source_payload)
        owner_run_id = str(source_summary.get("owner_run_id") or "").strip() or None
        run = _candidate_run(db, owner_run_id)
        artifact_payload = contract.build_deterministic_challenge_artifact_payload(source_payload, generated_at_utc=_utc_iso())
        if persist_artifact:
            artifact_path = deterministic_challenge_artifact_path(owner_run_id=str(owner_run_id or ""), deterministic_challenge_artifact_id=str(artifact_payload.get("deterministic_challenge_artifact_id") or ""), reports_dir=settings.connector_reports_dir)
            artifact_payload, artifact_ref = _persist_or_validate_deterministic_challenge_artifact(artifact_path=artifact_path, payload=artifact_payload)
            if run is not None:
                existing_refs = dict((run.query_plan_json or {}).get("aps_deterministic_challenge_artifact_report_refs") or {})
                artifact_refs = [str(item).strip() for item in list(existing_refs.get("aps_deterministic_challenge_artifacts") or []) if str(item).strip()]
                if artifact_ref not in artifact_refs:
                    artifact_refs.append(artifact_ref)
                failure_refs = [str(item).strip() for item in list(existing_refs.get("aps_deterministic_challenge_artifact_failures") or []) if str(item).strip()]
                source_insight = dict(artifact_payload.get("source_deterministic_insight_artifact") or {})
                summaries = _append_deterministic_challenge_artifact_summary(
                    (run.query_plan_json or {}).get("aps_deterministic_challenge_artifact_summaries"),
                    {
                        "deterministic_challenge_artifact_id": str(artifact_payload.get("deterministic_challenge_artifact_id") or ""),
                        "deterministic_challenge_artifact_checksum": str(artifact_payload.get("deterministic_challenge_artifact_checksum") or ""),
                        "ruleset_id": str(artifact_payload.get("ruleset_id") or ""),
                        "ruleset_version": int(artifact_payload.get("ruleset_version") or 0),
                        "source_deterministic_insight_artifact_id": str(source_insight.get("deterministic_insight_artifact_id") or ""),
                        "source_deterministic_insight_artifact_checksum": str(source_insight.get("deterministic_insight_artifact_checksum") or ""),
                        "owner_run_id": str(source_insight.get("owner_run_id") or ""),
                        "total_challenges": int(artifact_payload.get("total_challenges") or 0),
                        "challenge_counts": {severity: int(dict(artifact_payload.get("challenge_counts") or {}).get(severity, 0) or 0) for severity in contract.APS_CHALLENGE_SEVERITIES},
                        "disposition_counts": {disposition: int(dict(artifact_payload.get("disposition_counts") or {}).get(disposition, 0) or 0) for disposition in contract.APS_CHALLENGE_DISPOSITIONS},
                        "ref": artifact_ref,
                    },
                )
                run.query_plan_json = {
                    **(run.query_plan_json or {}),
                    "aps_deterministic_challenge_artifact_report_refs": {
                        "aps_deterministic_challenge_artifacts": artifact_refs,
                        "aps_deterministic_challenge_artifact_failures": failure_refs,
                    },
                    "aps_deterministic_challenge_artifact_summaries": summaries,
                }
                db.commit()
            artifact_payload["_deterministic_challenge_artifact_ref"] = artifact_ref
            artifact_payload["_persisted"] = True
        else:
            artifact_payload["_deterministic_challenge_artifact_ref"] = None
            artifact_payload["_persisted"] = False
        return _response_payload(artifact_payload)
    except DeterministicChallengeArtifactError as exc:
        if persist_artifact:
            _persist_failure_artifact(db, run=run, owner_run_id=owner_run_id, normalized_request=normalized_request, source_payload=source_payload, error_code=exc.code, error_message=exc.message)
        raise
    except Exception as exc:  # noqa: BLE001
        if persist_artifact:
            _persist_failure_artifact(db, run=run, owner_run_id=owner_run_id, normalized_request=normalized_request, source_payload=source_payload, error_code=contract.APS_RUNTIME_FAILURE_INTERNAL, error_message=str(exc))
        raise DeterministicChallengeArtifactError(contract.APS_RUNTIME_FAILURE_INTERNAL, str(exc), status_code=500) from exc


def get_persisted_deterministic_challenge_artifact(*, deterministic_challenge_artifact_id: str) -> dict[str, Any]:
    payload, _candidate_path = load_persisted_deterministic_challenge_artifact(deterministic_challenge_artifact_id=str(deterministic_challenge_artifact_id or "").strip())
    return _response_payload(payload)
