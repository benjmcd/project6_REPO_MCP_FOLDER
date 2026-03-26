from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from sqlalchemy.orm import Session

from app.core.config import settings
from app.models import ConnectorRun
from app.services import nrc_aps_deterministic_challenge_review_packet_contract as contract
from app.services import nrc_aps_deterministic_challenge_artifact
from app.services import nrc_aps_deterministic_challenge_artifact_contract as challenge_contract
from app.services import nrc_aps_safeguards


class DeterministicChallengeReviewPacketError(RuntimeError):
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
    if code in {contract.APS_RUNTIME_FAILURE_INVALID_REQUEST, contract.APS_RUNTIME_FAILURE_SOURCE_CHALLENGE_ARTIFACT_INVALID}:
        return 422
    if code in {contract.APS_RUNTIME_FAILURE_SOURCE_CHALLENGE_ARTIFACT_NOT_FOUND, contract.APS_RUNTIME_FAILURE_ARTIFACT_NOT_FOUND}:
        return 404
    if code in {contract.APS_RUNTIME_FAILURE_SOURCE_CHALLENGE_ARTIFACT_CONFLICT, contract.APS_RUNTIME_FAILURE_CONFLICT}:
        return 409
    if code in {contract.APS_RUNTIME_FAILURE_ARTIFACT_INVALID, contract.APS_RUNTIME_FAILURE_WRITE_FAILED, contract.APS_RUNTIME_FAILURE_INTERNAL}:
        return 500
    return 422


def deterministic_challenge_review_packet_path(*, owner_run_id: str, deterministic_challenge_review_packet_id: str, reports_dir: str | Path) -> Path:
    scope = f"run_{_safe_scope_token(owner_run_id)}"
    return Path(reports_dir) / contract.expected_deterministic_challenge_review_packet_file_name(
        scope=scope,
        deterministic_challenge_review_packet_id=deterministic_challenge_review_packet_id,
    )


def deterministic_challenge_review_packet_failure_path(*, owner_run_id: str, deterministic_challenge_review_packet_id: str, reports_dir: str | Path) -> Path:
    scope = f"run_{_safe_scope_token(owner_run_id)}"
    return Path(reports_dir) / contract.expected_failure_file_name(
        scope=scope,
        deterministic_challenge_review_packet_id=deterministic_challenge_review_packet_id,
    )


def _candidate_deterministic_challenge_review_packets_by_id(*, deterministic_challenge_review_packet_id: str, reports_dir: str | Path) -> list[Path]:
    pattern = f"*_{contract.artifact_id_token(deterministic_challenge_review_packet_id)}_aps_deterministic_challenge_review_packet_v1.json"
    return sorted(Path(reports_dir).glob(pattern), key=lambda path: path.name)


def _resolve_deterministic_challenge_review_packet_path(*, deterministic_challenge_review_packet_id: str | None = None, deterministic_challenge_review_packet_ref: str | Path | None = None) -> Path:
    normalized_id = str(deterministic_challenge_review_packet_id or "").strip()
    normalized_ref = str(deterministic_challenge_review_packet_ref or "").strip()
    if bool(normalized_id) == bool(normalized_ref):
        raise DeterministicChallengeReviewPacketError(contract.APS_RUNTIME_FAILURE_INVALID_REQUEST, "exactly one of deterministic_challenge_review_packet_id or deterministic_challenge_review_packet_ref is required", status_code=400)
    if normalized_ref:
        candidate_path = Path(normalized_ref)
    else:
        candidate_paths = _candidate_deterministic_challenge_review_packets_by_id(
            deterministic_challenge_review_packet_id=normalized_id,
            reports_dir=settings.connector_reports_dir,
        )
        if not candidate_paths:
            raise DeterministicChallengeReviewPacketError(contract.APS_RUNTIME_FAILURE_ARTIFACT_NOT_FOUND, "deterministic challenge review packet not found", status_code=404)
        if len(candidate_paths) > 1:
            raise DeterministicChallengeReviewPacketError(contract.APS_RUNTIME_FAILURE_CONFLICT, "deterministic challenge review packet id is ambiguous across run scopes; use deterministic_challenge_review_packet_ref", status_code=409)
        candidate_path = candidate_paths[0]
    if not candidate_path.exists():
        raise DeterministicChallengeReviewPacketError(contract.APS_RUNTIME_FAILURE_ARTIFACT_NOT_FOUND, "deterministic challenge review packet not found", status_code=404)
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
        raise DeterministicChallengeReviewPacketError(contract.APS_RUNTIME_FAILURE_ARTIFACT_INVALID, f"{field_name} missing", status_code=500)
    return value


def _as_required_non_negative_int(payload: dict[str, Any], field_name: str) -> int:
    value = payload.get(field_name)
    if isinstance(value, bool) or not isinstance(value, int) or int(value) < 0:
        raise DeterministicChallengeReviewPacketError(contract.APS_RUNTIME_FAILURE_ARTIFACT_INVALID, f"{field_name} invalid", status_code=500)
    return int(value)


def _validate_projection_identity(payload: dict[str, Any]) -> None:
    for field_name, expected_value in contract.projection_identity_payload().items():
        if payload.get(field_name) != expected_value:
            raise DeterministicChallengeReviewPacketError(contract.APS_RUNTIME_FAILURE_ARTIFACT_INVALID, f"{field_name} mismatch", status_code=500)


def _validate_source_deterministic_challenge_artifact_summary(payload: dict[str, Any]) -> dict[str, Any]:
    if str(payload.get("schema_id") or "") != challenge_contract.APS_DETERMINISTIC_CHALLENGE_ARTIFACT_SCHEMA_ID:
        raise DeterministicChallengeReviewPacketError(contract.APS_RUNTIME_FAILURE_ARTIFACT_INVALID, "source challenge schema mismatch", status_code=500)
    if int(payload.get("schema_version") or 0) != challenge_contract.APS_DETERMINISTIC_CHALLENGE_ARTIFACT_SCHEMA_VERSION:
        raise DeterministicChallengeReviewPacketError(contract.APS_RUNTIME_FAILURE_ARTIFACT_INVALID, "source challenge schema version mismatch", status_code=500)
    for field_name in (
        "deterministic_challenge_artifact_id",
        "deterministic_challenge_artifact_checksum",
        "deterministic_challenge_artifact_ref",
        "ruleset_contract_id",
        "ruleset_id",
        "challenge_mode",
    ):
        _as_required_text(payload, field_name)
    if str(payload.get("ruleset_contract_id") or "") != challenge_contract.APS_DETERMINISTIC_CHALLENGE_RULESET_CONTRACT_ID:
        raise DeterministicChallengeReviewPacketError(contract.APS_RUNTIME_FAILURE_ARTIFACT_INVALID, "source challenge ruleset contract mismatch", status_code=500)
    if str(payload.get("ruleset_id") or "") != challenge_contract.APS_DETERMINISTIC_CHALLENGE_RULESET_ID:
        raise DeterministicChallengeReviewPacketError(contract.APS_RUNTIME_FAILURE_ARTIFACT_INVALID, "source challenge ruleset id mismatch", status_code=500)
    if int(payload.get("ruleset_version") or 0) != challenge_contract.APS_DETERMINISTIC_CHALLENGE_RULESET_VERSION:
        raise DeterministicChallengeReviewPacketError(contract.APS_RUNTIME_FAILURE_ARTIFACT_INVALID, "source challenge ruleset version mismatch", status_code=500)
    if str(payload.get("challenge_mode") or "") != challenge_contract.APS_DETERMINISTIC_CHALLENGE_MODE:
        raise DeterministicChallengeReviewPacketError(contract.APS_RUNTIME_FAILURE_ARTIFACT_INVALID, "source challenge mode mismatch", status_code=500)
    _as_required_non_negative_int(payload, "total_challenges")
    if not isinstance(payload.get("source_deterministic_insight_artifact"), dict):
        raise DeterministicChallengeReviewPacketError(contract.APS_RUNTIME_FAILURE_ARTIFACT_INVALID, "source insight lineage missing", status_code=500)
    return payload


def _validate_bucket_challenge_row(row: dict[str, Any]) -> None:
    _as_required_text(row, "challenge_id")
    _as_required_text(row, "check_id")
    _as_required_non_negative_int(row, "check_version")
    _as_required_text(row, "category")
    _as_required_text(row, "severity")
    _as_required_text(row, "disposition")
    _as_required_non_negative_int(row, "matched_finding_count")


def _validate_failure_payload_schema(payload: dict[str, Any]) -> dict[str, Any]:
    if str(payload.get("schema_id") or "") != contract.APS_DETERMINISTIC_CHALLENGE_REVIEW_PACKET_FAILURE_SCHEMA_ID:
        raise DeterministicChallengeReviewPacketError(contract.APS_RUNTIME_FAILURE_ARTIFACT_INVALID, "failure schema mismatch", status_code=500)
    if int(payload.get("schema_version") or 0) != contract.APS_DETERMINISTIC_CHALLENGE_REVIEW_PACKET_SCHEMA_VERSION:
        raise DeterministicChallengeReviewPacketError(contract.APS_RUNTIME_FAILURE_ARTIFACT_INVALID, "failure schema version mismatch", status_code=500)
    _validate_projection_identity(payload)
    _as_required_text(payload, "deterministic_challenge_review_packet_id")
    _as_required_text(payload, "owner_run_id")
    _as_required_text(payload, "error_code")
    if not isinstance(payload.get("source_request"), dict):
        raise DeterministicChallengeReviewPacketError(contract.APS_RUNTIME_FAILURE_ARTIFACT_INVALID, "source request mismatch", status_code=500)
    if not isinstance(payload.get("source_deterministic_challenge_artifact"), dict):
        raise DeterministicChallengeReviewPacketError(contract.APS_RUNTIME_FAILURE_ARTIFACT_INVALID, "source challenge mismatch", status_code=500)
    checksum = str(payload.get("deterministic_challenge_review_packet_checksum") or "").strip()
    if not checksum or checksum != contract.compute_deterministic_challenge_review_packet_checksum(payload):
        raise DeterministicChallengeReviewPacketError(contract.APS_RUNTIME_FAILURE_ARTIFACT_INVALID, "failure checksum mismatch", status_code=500)
    return payload


def _validate_persisted_deterministic_challenge_review_packet_payload(payload: dict[str, Any]) -> dict[str, Any]:
    if str(payload.get("schema_id") or "") != contract.APS_DETERMINISTIC_CHALLENGE_REVIEW_PACKET_SCHEMA_ID:
        raise DeterministicChallengeReviewPacketError(contract.APS_RUNTIME_FAILURE_ARTIFACT_INVALID, "artifact schema mismatch", status_code=500)
    if int(payload.get("schema_version") or 0) != contract.APS_DETERMINISTIC_CHALLENGE_REVIEW_PACKET_SCHEMA_VERSION:
        raise DeterministicChallengeReviewPacketError(contract.APS_RUNTIME_FAILURE_ARTIFACT_INVALID, "artifact schema version mismatch", status_code=500)
    _validate_projection_identity(payload)
    source_summary = _validate_source_deterministic_challenge_artifact_summary(dict(payload.get("source_deterministic_challenge_artifact") or {}))
    expected_packet_id = contract.derive_deterministic_challenge_review_packet_id(
        source_deterministic_challenge_artifact_id=str(source_summary.get("deterministic_challenge_artifact_id") or "")
    )
    if str(payload.get("deterministic_challenge_review_packet_id") or "").strip() != expected_packet_id:
        raise DeterministicChallengeReviewPacketError(contract.APS_RUNTIME_FAILURE_ARTIFACT_INVALID, "artifact id mismatch", status_code=500)
    total_challenges = _as_required_non_negative_int(payload, "total_challenges")
    blocker_count = _as_required_non_negative_int(payload, "blocker_count")
    review_item_count = _as_required_non_negative_int(payload, "review_item_count")
    acknowledgement_count = _as_required_non_negative_int(payload, "acknowledgement_count")
    blockers = [dict(item or {}) for item in list(payload.get("blockers") or []) if isinstance(item, dict)]
    review_items = [dict(item or {}) for item in list(payload.get("review_items") or []) if isinstance(item, dict)]
    acknowledgements = [dict(item or {}) for item in list(payload.get("acknowledgements") or []) if isinstance(item, dict)]
    if blocker_count != len(blockers):
        raise DeterministicChallengeReviewPacketError(contract.APS_RUNTIME_FAILURE_ARTIFACT_INVALID, "blocker count mismatch", status_code=500)
    if review_item_count != len(review_items):
        raise DeterministicChallengeReviewPacketError(contract.APS_RUNTIME_FAILURE_ARTIFACT_INVALID, "review item count mismatch", status_code=500)
    if acknowledgement_count != len(acknowledgements):
        raise DeterministicChallengeReviewPacketError(contract.APS_RUNTIME_FAILURE_ARTIFACT_INVALID, "acknowledgement count mismatch", status_code=500)
    if total_challenges != blocker_count + review_item_count + acknowledgement_count:
        raise DeterministicChallengeReviewPacketError(contract.APS_RUNTIME_FAILURE_ARTIFACT_INVALID, "total challenges mismatch", status_code=500)
    for row in blockers + review_items + acknowledgements:
        _validate_bucket_challenge_row(row)
    checksum = str(payload.get("deterministic_challenge_review_packet_checksum") or "").strip()
    if not checksum or checksum != contract.compute_deterministic_challenge_review_packet_checksum(payload):
        raise DeterministicChallengeReviewPacketError(contract.APS_RUNTIME_FAILURE_ARTIFACT_INVALID, "artifact checksum mismatch", status_code=500)
    return payload


def load_persisted_deterministic_challenge_review_packet(*, deterministic_challenge_review_packet_id: str | None = None, deterministic_challenge_review_packet_ref: str | Path | None = None) -> tuple[dict[str, Any], Path]:
    candidate_path = _resolve_deterministic_challenge_review_packet_path(
        deterministic_challenge_review_packet_id=deterministic_challenge_review_packet_id,
        deterministic_challenge_review_packet_ref=deterministic_challenge_review_packet_ref,
    )
    payload = _read_json(candidate_path)
    if not payload:
        raise DeterministicChallengeReviewPacketError(contract.APS_RUNTIME_FAILURE_ARTIFACT_INVALID, "deterministic challenge review packet unreadable", status_code=500)
    validated_payload = _validate_persisted_deterministic_challenge_review_packet_payload(payload)
    validated_payload["_deterministic_challenge_review_packet_ref"] = str(candidate_path)
    validated_payload["_persisted"] = True
    return validated_payload, candidate_path


def _conflict_error(message: str, *, inner_code: str | None = None) -> DeterministicChallengeReviewPacketError:
    details = f"{message}: {inner_code}" if inner_code else message
    return DeterministicChallengeReviewPacketError(contract.APS_RUNTIME_FAILURE_CONFLICT, details, status_code=409)


def _persist_or_validate_deterministic_challenge_review_packet(*, artifact_path: Path, payload: dict[str, Any]) -> tuple[dict[str, Any], str]:
    if artifact_path.exists():
        try:
            existing_payload, existing_path = load_persisted_deterministic_challenge_review_packet(deterministic_challenge_review_packet_ref=artifact_path)
        except DeterministicChallengeReviewPacketError as exc:
            raise _conflict_error("existing persisted deterministic challenge review packet conflicts with derived artifact", inner_code=contract.APS_RUNTIME_FAILURE_ARTIFACT_INVALID) from exc
        if str(existing_payload.get("deterministic_challenge_review_packet_id") or "").strip() != str(payload.get("deterministic_challenge_review_packet_id") or "").strip():
            raise _conflict_error("existing persisted deterministic challenge review packet id conflicts with derived artifact")
        if str(existing_payload.get("deterministic_challenge_review_packet_checksum") or "").strip() != str(payload.get("deterministic_challenge_review_packet_checksum") or "").strip():
            raise _conflict_error("existing persisted deterministic challenge review packet checksum conflicts with derived artifact")
        if contract.logical_deterministic_challenge_review_packet_payload(existing_payload) != contract.logical_deterministic_challenge_review_packet_payload(payload):
            raise _conflict_error("existing persisted deterministic challenge review packet body conflicts with derived artifact")
        return existing_payload, str(existing_path)
    artifact_ref = nrc_aps_safeguards.write_json_atomic(artifact_path, payload)
    validated_payload, _validated_path = load_persisted_deterministic_challenge_review_packet(deterministic_challenge_review_packet_ref=artifact_ref)
    return validated_payload, artifact_ref


def _append_deterministic_challenge_review_packet_summary(existing: list[dict[str, Any]] | None, entry: dict[str, Any]) -> list[dict[str, Any]]:
    summaries = [dict(item or {}) for item in (existing or []) if isinstance(item, dict)]
    incoming_packet_id = str(entry.get("deterministic_challenge_review_packet_id") or "").strip()
    incoming_ref = str(entry.get("ref") or "").strip()
    kept: list[dict[str, Any]] = []
    replaced = False
    for item in summaries:
        same_packet_id = str(item.get("deterministic_challenge_review_packet_id") or "").strip() == incoming_packet_id
        same_ref = incoming_ref and str(item.get("ref") or "").strip() == incoming_ref
        if same_packet_id or same_ref:
            if not replaced:
                kept.append(dict(entry))
                replaced = True
            continue
        kept.append(item)
    if not replaced:
        kept.append(dict(entry))
    kept.sort(key=lambda item: (str(item.get("deterministic_challenge_review_packet_id") or ""), str(item.get("ref") or "")))
    return kept


def _candidate_run(db: Session, run_id: str | None) -> ConnectorRun | None:
    normalized_run_id = str(run_id or "").strip()
    if not normalized_run_id:
        return None
    return db.get(ConnectorRun, normalized_run_id)


def _response_payload(payload: dict[str, Any]) -> dict[str, Any]:
    return {
        "generated_at_utc": str(payload.get("generated_at_utc") or ""),
        "schema_id": str(payload.get("schema_id") or contract.APS_DETERMINISTIC_CHALLENGE_REVIEW_PACKET_SCHEMA_ID),
        "schema_version": int(payload.get("schema_version") or contract.APS_DETERMINISTIC_CHALLENGE_REVIEW_PACKET_SCHEMA_VERSION),
        "deterministic_challenge_review_packet_id": str(payload.get("deterministic_challenge_review_packet_id") or ""),
        "deterministic_challenge_review_packet_checksum": str(payload.get("deterministic_challenge_review_packet_checksum") or ""),
        "deterministic_challenge_review_packet_ref": str(payload.get("_deterministic_challenge_review_packet_ref") or "") or None,
        "projection_contract_id": str(payload.get("projection_contract_id") or contract.APS_DETERMINISTIC_CHALLENGE_REVIEW_PACKET_PROJECTION_CONTRACT_ID),
        "projection_mode": str(payload.get("projection_mode") or contract.APS_DETERMINISTIC_CHALLENGE_REVIEW_PACKET_PROJECTION_MODE),
        "source_deterministic_challenge_artifact": dict(payload.get("source_deterministic_challenge_artifact") or {}),
        "total_challenges": int(payload.get("total_challenges") or 0),
        "blocker_count": int(payload.get("blocker_count") or 0),
        "review_item_count": int(payload.get("review_item_count") or 0),
        "acknowledgement_count": int(payload.get("acknowledgement_count") or 0),
        "blockers": [dict(item or {}) for item in list(payload.get("blockers") or []) if isinstance(item, dict)],
        "review_items": [dict(item or {}) for item in list(payload.get("review_items") or []) if isinstance(item, dict)],
        "acknowledgements": [dict(item or {}) for item in list(payload.get("acknowledgements") or []) if isinstance(item, dict)],
        "persisted": bool(payload.get("_persisted", False)),
    }


def _source_challenge_error(exc: nrc_aps_deterministic_challenge_artifact.DeterministicChallengeArtifactError) -> DeterministicChallengeReviewPacketError:
    if int(exc.status_code) == 404:
        code = contract.APS_RUNTIME_FAILURE_SOURCE_CHALLENGE_ARTIFACT_NOT_FOUND
    elif int(exc.status_code) == 409:
        code = contract.APS_RUNTIME_FAILURE_SOURCE_CHALLENGE_ARTIFACT_CONFLICT
    else:
        code = contract.APS_RUNTIME_FAILURE_SOURCE_CHALLENGE_ARTIFACT_INVALID
    return DeterministicChallengeReviewPacketError(code, str(exc.message), status_code=_status_for_error_code(code))


def _resolve_source_deterministic_challenge_artifact_payload(normalized_request: dict[str, Any]) -> tuple[dict[str, Any], Path]:
    try:
        return nrc_aps_deterministic_challenge_artifact.load_persisted_deterministic_challenge_artifact(
            deterministic_challenge_artifact_id=normalized_request.get("deterministic_challenge_artifact_id"),
            deterministic_challenge_artifact_ref=normalized_request.get("deterministic_challenge_artifact_ref"),
        )
    except nrc_aps_deterministic_challenge_artifact.DeterministicChallengeArtifactError as exc:
        raise _source_challenge_error(exc) from exc


def _failure_source_locator(normalized_request: dict[str, Any]) -> str:
    return str(normalized_request.get("deterministic_challenge_artifact_id") or normalized_request.get("deterministic_challenge_artifact_ref") or "unknown")


def _owner_run_id_from_challenge(source_payload: dict[str, Any]) -> str | None:
    source_insight = dict(source_payload.get("source_deterministic_insight_artifact") or {})
    return str(source_insight.get("owner_run_id") or "").strip() or None


def _persist_failure_artifact(db: Session, *, run: ConnectorRun | None, owner_run_id: str | None, normalized_request: dict[str, Any], source_payload: dict[str, Any] | None, error_code: str, error_message: str) -> str | None:
    effective_owner_run_id = str(owner_run_id or getattr(run, "connector_run_id", "") or "").strip()
    if not effective_owner_run_id:
        return None
    failure_packet_id = contract.derive_failure_deterministic_challenge_review_packet_id(source_locator=_failure_source_locator(normalized_request), error_code=error_code)
    source_summary = {
        "deterministic_challenge_artifact_id": None,
        "deterministic_challenge_artifact_checksum": None,
        "deterministic_challenge_artifact_ref": None,
    }
    if isinstance(source_payload, dict) and source_payload:
        source_summary = {
            "deterministic_challenge_artifact_id": str(source_payload.get("deterministic_challenge_artifact_id") or "").strip() or None,
            "deterministic_challenge_artifact_checksum": str(source_payload.get("deterministic_challenge_artifact_checksum") or "").strip() or None,
            "deterministic_challenge_artifact_ref": str(source_payload.get("_deterministic_challenge_artifact_ref") or source_payload.get("deterministic_challenge_artifact_ref") or "").strip() or None,
        }
    failure_payload: dict[str, Any] = {
        "schema_id": contract.APS_DETERMINISTIC_CHALLENGE_REVIEW_PACKET_FAILURE_SCHEMA_ID,
        "schema_version": contract.APS_DETERMINISTIC_CHALLENGE_REVIEW_PACKET_SCHEMA_VERSION,
        "generated_at_utc": _utc_iso(),
        "deterministic_challenge_review_packet_id": failure_packet_id,
        **contract.projection_identity_payload(),
        "owner_run_id": effective_owner_run_id,
        "source_request": {
            "deterministic_challenge_artifact_id": normalized_request.get("deterministic_challenge_artifact_id"),
            "deterministic_challenge_artifact_ref": normalized_request.get("deterministic_challenge_artifact_ref"),
            "persist_review_packet": bool(normalized_request.get("persist_review_packet", False)),
        },
        "source_deterministic_challenge_artifact": source_summary,
        "error_code": str(error_code or contract.APS_RUNTIME_FAILURE_INTERNAL),
        "error_message": str(error_message or ""),
    }
    failure_payload["deterministic_challenge_review_packet_checksum"] = contract.compute_deterministic_challenge_review_packet_checksum(failure_payload)
    failure_path = deterministic_challenge_review_packet_failure_path(owner_run_id=effective_owner_run_id, deterministic_challenge_review_packet_id=failure_packet_id, reports_dir=settings.connector_reports_dir)
    failure_ref = nrc_aps_safeguards.write_json_atomic(failure_path, failure_payload)
    if run is None:
        return failure_ref
    existing_refs = dict((run.query_plan_json or {}).get("aps_deterministic_challenge_review_packet_report_refs") or {})
    failure_refs = [str(item).strip() for item in list(existing_refs.get("aps_deterministic_challenge_review_packet_failures") or []) if str(item).strip()]
    if failure_ref not in failure_refs:
        failure_refs.append(failure_ref)
    run.query_plan_json = {
        **(run.query_plan_json or {}),
        "aps_deterministic_challenge_review_packet_report_refs": {
            "aps_deterministic_challenge_review_packets": [str(item).strip() for item in list(existing_refs.get("aps_deterministic_challenge_review_packets") or []) if str(item).strip()],
            "aps_deterministic_challenge_review_packet_failures": failure_refs,
        },
    }
    db.commit()
    return failure_ref


def assemble_deterministic_challenge_review_packet(db: Session, *, request_payload: dict[str, Any]) -> dict[str, Any]:
    try:
        normalized_request = contract.normalize_request_payload(request_payload)
    except ValueError as exc:
        code = str(exc) or contract.APS_RUNTIME_FAILURE_INVALID_REQUEST
        raise DeterministicChallengeReviewPacketError(code, f"invalid request: {code}", status_code=_status_for_error_code(code)) from None
    persist_artifact = bool(normalized_request.get("persist_review_packet", False))
    source_payload: dict[str, Any] | None = None
    run: ConnectorRun | None = None
    owner_run_id: str | None = None
    try:
        source_payload, _source_path = _resolve_source_deterministic_challenge_artifact_payload(normalized_request)
        owner_run_id = _owner_run_id_from_challenge(source_payload)
        run = _candidate_run(db, owner_run_id)
        packet_payload = contract.build_deterministic_challenge_review_packet_payload(source_payload, generated_at_utc=_utc_iso())
        if persist_artifact:
            artifact_path = deterministic_challenge_review_packet_path(owner_run_id=str(owner_run_id or ""), deterministic_challenge_review_packet_id=str(packet_payload.get("deterministic_challenge_review_packet_id") or ""), reports_dir=settings.connector_reports_dir)
            packet_payload, artifact_ref = _persist_or_validate_deterministic_challenge_review_packet(artifact_path=artifact_path, payload=packet_payload)
            if run is not None:
                existing_refs = dict((run.query_plan_json or {}).get("aps_deterministic_challenge_review_packet_report_refs") or {})
                artifact_refs = [str(item).strip() for item in list(existing_refs.get("aps_deterministic_challenge_review_packets") or []) if str(item).strip()]
                if artifact_ref not in artifact_refs:
                    artifact_refs.append(artifact_ref)
                failure_refs = [str(item).strip() for item in list(existing_refs.get("aps_deterministic_challenge_review_packet_failures") or []) if str(item).strip()]
                source_challenge = dict(packet_payload.get("source_deterministic_challenge_artifact") or {})
                summaries = _append_deterministic_challenge_review_packet_summary(
                    (run.query_plan_json or {}).get("aps_deterministic_challenge_review_packet_summaries"),
                    {
                        "deterministic_challenge_review_packet_id": str(packet_payload.get("deterministic_challenge_review_packet_id") or ""),
                        "deterministic_challenge_review_packet_checksum": str(packet_payload.get("deterministic_challenge_review_packet_checksum") or ""),
                        "projection_contract_id": str(packet_payload.get("projection_contract_id") or ""),
                        "source_deterministic_challenge_artifact_id": str(source_challenge.get("deterministic_challenge_artifact_id") or ""),
                        "source_deterministic_challenge_artifact_checksum": str(source_challenge.get("deterministic_challenge_artifact_checksum") or ""),
                        "owner_run_id": str(owner_run_id or ""),
                        "total_challenges": int(packet_payload.get("total_challenges") or 0),
                        "blocker_count": int(packet_payload.get("blocker_count") or 0),
                        "review_item_count": int(packet_payload.get("review_item_count") or 0),
                        "acknowledgement_count": int(packet_payload.get("acknowledgement_count") or 0),
                        "ref": artifact_ref,
                    },
                )
                run.query_plan_json = {
                    **(run.query_plan_json or {}),
                    "aps_deterministic_challenge_review_packet_report_refs": {
                        "aps_deterministic_challenge_review_packets": artifact_refs,
                        "aps_deterministic_challenge_review_packet_failures": failure_refs,
                    },
                    "aps_deterministic_challenge_review_packet_summaries": summaries,
                }
                db.commit()
            packet_payload["_deterministic_challenge_review_packet_ref"] = artifact_ref
            packet_payload["_persisted"] = True
        else:
            packet_payload["_deterministic_challenge_review_packet_ref"] = None
            packet_payload["_persisted"] = False
        return _response_payload(packet_payload)
    except DeterministicChallengeReviewPacketError as exc:
        if persist_artifact:
            _persist_failure_artifact(db, run=run, owner_run_id=owner_run_id, normalized_request=normalized_request, source_payload=source_payload, error_code=exc.code, error_message=exc.message)
        raise
    except Exception as exc:  # noqa: BLE001
        if persist_artifact:
            _persist_failure_artifact(db, run=run, owner_run_id=owner_run_id, normalized_request=normalized_request, source_payload=source_payload, error_code=contract.APS_RUNTIME_FAILURE_INTERNAL, error_message=str(exc))
        raise DeterministicChallengeReviewPacketError(contract.APS_RUNTIME_FAILURE_INTERNAL, str(exc), status_code=500) from exc


def get_persisted_deterministic_challenge_review_packet(*, deterministic_challenge_review_packet_id: str) -> dict[str, Any]:
    payload, _candidate_path = load_persisted_deterministic_challenge_review_packet(deterministic_challenge_review_packet_id=str(deterministic_challenge_review_packet_id or "").strip())
    return _response_payload(payload)
