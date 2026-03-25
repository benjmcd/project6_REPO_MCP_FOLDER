from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from sqlalchemy.orm import Session

from app.core.config import settings
from app.models import ConnectorRun
from app.services import nrc_aps_context_dossier_contract as contract
from app.services import nrc_aps_context_packet
from app.services import nrc_aps_safeguards


class ContextDossierError(RuntimeError):
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
        contract.APS_RUNTIME_FAILURE_DUPLICATE_SOURCE_PACKET,
        contract.APS_RUNTIME_FAILURE_TOO_FEW_SOURCE_PACKETS,
        contract.APS_RUNTIME_FAILURE_TOO_MANY_SOURCE_PACKETS,
        contract.APS_RUNTIME_FAILURE_SOURCE_PACKET_INVALID,
    }:
        return 422
    if code in {contract.APS_RUNTIME_FAILURE_SOURCE_PACKET_NOT_FOUND, contract.APS_RUNTIME_FAILURE_DOSSIER_NOT_FOUND}:
        return 404
    if code in {
        contract.APS_RUNTIME_FAILURE_CROSS_RUN_UNSUPPORTED,
        contract.APS_RUNTIME_FAILURE_SOURCE_PACKET_INCOMPATIBLE,
        contract.APS_RUNTIME_FAILURE_CONFLICT,
    }:
        return 409
    if code in {contract.APS_RUNTIME_FAILURE_WRITE_FAILED, contract.APS_RUNTIME_FAILURE_INTERNAL}:
        return 500
    return 422


def _parse_incompatibility_or_error_code(raw: str) -> tuple[str, str | None]:
    text = str(raw or "").strip()
    if text == contract.APS_RUNTIME_FAILURE_CROSS_RUN_UNSUPPORTED:
        return contract.APS_RUNTIME_FAILURE_CROSS_RUN_UNSUPPORTED, None
    if text.startswith(f"{contract.APS_RUNTIME_FAILURE_SOURCE_PACKET_INCOMPATIBLE}:"):
        _prefix, reason = text.split(":", 1)
        reason_text = str(reason or "").strip() or None
        return contract.APS_RUNTIME_FAILURE_SOURCE_PACKET_INCOMPATIBLE, reason_text
    if text.startswith(f"{contract.APS_RUNTIME_FAILURE_SOURCE_PACKET_INVALID}:"):
        return contract.APS_RUNTIME_FAILURE_SOURCE_PACKET_INVALID, None
    if text:
        return text, None
    return contract.APS_RUNTIME_FAILURE_INTERNAL, None


def context_dossier_artifact_path(
    *,
    owner_run_id: str,
    context_dossier_id: str,
    reports_dir: str | Path,
) -> Path:
    scope = f"run_{_safe_scope_token(owner_run_id)}"
    return Path(reports_dir) / contract.expected_context_dossier_file_name(
        scope=scope,
        context_dossier_id=context_dossier_id,
    )


def context_dossier_failure_artifact_path(
    *,
    owner_run_id: str,
    context_dossier_id: str,
    reports_dir: str | Path,
) -> Path:
    scope = f"run_{_safe_scope_token(owner_run_id)}"
    return Path(reports_dir) / contract.expected_failure_file_name(
        scope=scope,
        context_dossier_id=context_dossier_id,
    )


def _candidate_context_dossier_artifacts_by_id(*, context_dossier_id: str, reports_dir: str | Path) -> list[Path]:
    pattern = f"*_{contract.artifact_id_token(context_dossier_id)}_aps_context_dossier_v1.json"
    return sorted(Path(reports_dir).glob(pattern), key=lambda path: path.name)


def find_context_dossier_artifact_by_id(*, context_dossier_id: str, reports_dir: str | Path) -> Path | None:
    candidates = _candidate_context_dossier_artifacts_by_id(
        context_dossier_id=context_dossier_id,
        reports_dir=reports_dir,
    )
    if not candidates:
        return None
    return candidates[0]


def _resolve_context_dossier_artifact_path(
    *,
    context_dossier_id: str | None = None,
    context_dossier_ref: str | Path | None = None,
) -> Path:
    normalized_context_dossier_id = str(context_dossier_id or "").strip()
    normalized_context_dossier_ref = str(context_dossier_ref or "").strip()
    if bool(normalized_context_dossier_id) == bool(normalized_context_dossier_ref):
        raise ContextDossierError(
            contract.APS_RUNTIME_FAILURE_INVALID_REQUEST,
            "exactly one of context_dossier_id or context_dossier_ref is required",
            status_code=400,
        )
    if normalized_context_dossier_ref:
        candidate_path = Path(normalized_context_dossier_ref)
    else:
        candidate_paths = _candidate_context_dossier_artifacts_by_id(
            context_dossier_id=normalized_context_dossier_id,
            reports_dir=settings.connector_reports_dir,
        )
        if not candidate_paths:
            raise ContextDossierError(
                contract.APS_RUNTIME_FAILURE_DOSSIER_NOT_FOUND,
                "context dossier not found",
                status_code=404,
            )
        if len(candidate_paths) > 1:
            raise ContextDossierError(
                contract.APS_RUNTIME_FAILURE_CONFLICT,
                "context dossier id is ambiguous across run scopes; use context_dossier_ref",
                status_code=409,
            )
        candidate_path = candidate_paths[0]
    if not candidate_path.exists():
        raise ContextDossierError(
            contract.APS_RUNTIME_FAILURE_DOSSIER_NOT_FOUND,
            "context dossier not found",
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


def _as_required_non_negative_int(payload: dict[str, Any], field_name: str) -> int:
    value = payload.get(field_name)
    if isinstance(value, bool):
        raise ContextDossierError(contract.APS_RUNTIME_FAILURE_DOSSIER_INVALID, f"{field_name} invalid", status_code=500)
    if not isinstance(value, int) or int(value) < 0:
        raise ContextDossierError(contract.APS_RUNTIME_FAILURE_DOSSIER_INVALID, f"{field_name} invalid", status_code=500)
    return int(value)


def _as_required_text(payload: dict[str, Any], field_name: str) -> str:
    value = str(payload.get(field_name) or "").strip()
    if not value:
        raise ContextDossierError(contract.APS_RUNTIME_FAILURE_DOSSIER_INVALID, f"{field_name} missing", status_code=500)
    return value


def _validate_failure_payload_schema(payload: dict[str, Any]) -> dict[str, Any]:
    if str(payload.get("schema_id") or "") != contract.APS_CONTEXT_DOSSIER_FAILURE_SCHEMA_ID:
        raise ContextDossierError(contract.APS_RUNTIME_FAILURE_DOSSIER_INVALID, "context dossier failure schema mismatch", status_code=500)
    if int(payload.get("schema_version") or 0) != contract.APS_CONTEXT_DOSSIER_SCHEMA_VERSION:
        raise ContextDossierError(
            contract.APS_RUNTIME_FAILURE_DOSSIER_INVALID,
            "context dossier failure schema version mismatch",
            status_code=500,
        )
    if str(payload.get("composition_contract_id") or "") != contract.APS_CONTEXT_DOSSIER_COMPOSITION_CONTRACT_ID:
        raise ContextDossierError(contract.APS_RUNTIME_FAILURE_DOSSIER_INVALID, "composition contract mismatch", status_code=500)
    if str(payload.get("dossier_mode") or "") != contract.APS_CONTEXT_DOSSIER_MODE:
        raise ContextDossierError(contract.APS_RUNTIME_FAILURE_DOSSIER_INVALID, "dossier mode mismatch", status_code=500)
    _as_required_text(payload, "context_dossier_id")
    _as_required_text(payload, "owner_run_id")
    _as_required_text(payload, "error_code")
    if payload.get("source_request") is None or not isinstance(payload.get("source_request"), dict):
        raise ContextDossierError(contract.APS_RUNTIME_FAILURE_DOSSIER_INVALID, "source request mismatch", status_code=500)
    source_packets = [dict(item or {}) for item in list(payload.get("source_packets") or []) if isinstance(item, dict)]
    for source_packet in source_packets:
        _as_required_text(source_packet, "context_packet_id")
        _as_required_text(source_packet, "context_packet_checksum")
        _as_required_text(source_packet, "context_packet_ref")
    checksum = str(payload.get("context_dossier_checksum") or "").strip()
    expected_checksum = contract.compute_context_dossier_checksum(payload)
    if not checksum or checksum != expected_checksum:
        raise ContextDossierError(contract.APS_RUNTIME_FAILURE_DOSSIER_INVALID, "context dossier failure checksum mismatch", status_code=500)
    return payload


def _validate_persisted_context_dossier_payload(payload: dict[str, Any]) -> dict[str, Any]:
    if str(payload.get("schema_id") or "") != contract.APS_CONTEXT_DOSSIER_SCHEMA_ID:
        raise ContextDossierError(contract.APS_RUNTIME_FAILURE_DOSSIER_INVALID, "context dossier schema mismatch", status_code=500)
    if int(payload.get("schema_version") or 0) != contract.APS_CONTEXT_DOSSIER_SCHEMA_VERSION:
        raise ContextDossierError(contract.APS_RUNTIME_FAILURE_DOSSIER_INVALID, "context dossier schema version mismatch", status_code=500)
    if str(payload.get("composition_contract_id") or "") != contract.APS_CONTEXT_DOSSIER_COMPOSITION_CONTRACT_ID:
        raise ContextDossierError(contract.APS_RUNTIME_FAILURE_DOSSIER_INVALID, "composition contract mismatch", status_code=500)
    if str(payload.get("dossier_mode") or "") != contract.APS_CONTEXT_DOSSIER_MODE:
        raise ContextDossierError(contract.APS_RUNTIME_FAILURE_DOSSIER_INVALID, "dossier mode mismatch", status_code=500)

    source_packets = [dict(item or {}) for item in list(payload.get("source_packets") or []) if isinstance(item, dict)]
    source_packet_count = _as_required_non_negative_int(payload, "source_packet_count")
    if source_packet_count != len(source_packets):
        raise ContextDossierError(contract.APS_RUNTIME_FAILURE_DOSSIER_INVALID, "source packet count mismatch", status_code=500)
    if len(source_packets) < contract.APS_CONTEXT_DOSSIER_MIN_SOURCES:
        raise ContextDossierError(contract.APS_RUNTIME_FAILURE_DOSSIER_INVALID, "too few source packets", status_code=500)

    seen_context_packet_ids: set[str] = set()
    for index, source_packet in enumerate(source_packets, start=1):
        if int(source_packet.get("packet_ordinal") or 0) != index:
            raise ContextDossierError(contract.APS_RUNTIME_FAILURE_DOSSIER_INVALID, "source packet ordinal mismatch", status_code=500)
        context_packet_id = _as_required_text(source_packet, "context_packet_id")
        _as_required_text(source_packet, "context_packet_checksum")
        _as_required_text(source_packet, "context_packet_ref")
        _as_required_text(source_packet, "source_family")
        _as_required_text(source_packet, "source_id")
        _as_required_text(source_packet, "source_checksum")
        _as_required_text(source_packet, "owner_run_id")
        _as_required_text(source_packet, "projection_contract_id")
        _as_required_text(source_packet, "fact_grammar_contract_id")
        _as_required_text(source_packet, "objective")
        _as_required_non_negative_int(source_packet, "total_facts")
        _as_required_non_negative_int(source_packet, "total_caveats")
        _as_required_non_negative_int(source_packet, "total_constraints")
        _as_required_non_negative_int(source_packet, "total_unresolved_questions")
        if context_packet_id in seen_context_packet_ids:
            raise ContextDossierError(contract.APS_RUNTIME_FAILURE_DOSSIER_INVALID, "duplicate source packet id", status_code=500)
        seen_context_packet_ids.add(context_packet_id)

    ordered_digest = _as_required_text(payload, "ordered_source_packets_sha256")
    expected_ordered_digest = contract.ordered_source_packets_sha256(source_packets)
    if ordered_digest != expected_ordered_digest:
        raise ContextDossierError(contract.APS_RUNTIME_FAILURE_DOSSIER_INVALID, "ordered source packets digest mismatch", status_code=500)

    expected_compatibility = contract.validate_source_packet_compatibility(
        [
            {
                "schema_id": contract.APS_CONTEXT_DOSSIER_EXPECTED_SOURCE_SCHEMA_ID,
                "schema_version": contract.APS_CONTEXT_DOSSIER_EXPECTED_SOURCE_SCHEMA_VERSION,
                "context_packet_id": source_packet.get("context_packet_id"),
                "context_packet_checksum": source_packet.get("context_packet_checksum"),
                "projection_contract_id": source_packet.get("projection_contract_id"),
                "fact_grammar_contract_id": source_packet.get("fact_grammar_contract_id"),
                "objective": source_packet.get("objective"),
                "source_family": source_packet.get("source_family"),
                "source_descriptor": {
                    "source_id": source_packet.get("source_id"),
                    "source_checksum": source_packet.get("source_checksum"),
                    "owner_run_id": source_packet.get("owner_run_id"),
                },
                "total_facts": source_packet.get("total_facts"),
                "total_caveats": source_packet.get("total_caveats"),
                "total_constraints": source_packet.get("total_constraints"),
                "total_unresolved_questions": source_packet.get("total_unresolved_questions"),
            }
            for source_packet in source_packets
        ]
    )
    if str(payload.get("owner_run_id") or "") != str(expected_compatibility.get("owner_run_id") or ""):
        raise ContextDossierError(contract.APS_RUNTIME_FAILURE_DOSSIER_INVALID, "owner run mismatch", status_code=500)
    if str(payload.get("projection_contract_id") or "") != str(expected_compatibility.get("projection_contract_id") or ""):
        raise ContextDossierError(contract.APS_RUNTIME_FAILURE_DOSSIER_INVALID, "projection contract mismatch", status_code=500)
    if str(payload.get("fact_grammar_contract_id") or "") != str(expected_compatibility.get("fact_grammar_contract_id") or ""):
        raise ContextDossierError(contract.APS_RUNTIME_FAILURE_DOSSIER_INVALID, "fact grammar contract mismatch", status_code=500)
    if str(payload.get("objective") or "") != str(expected_compatibility.get("objective") or ""):
        raise ContextDossierError(contract.APS_RUNTIME_FAILURE_DOSSIER_INVALID, "objective mismatch", status_code=500)
    if str(payload.get("source_family") or "") != str(expected_compatibility.get("source_family") or ""):
        raise ContextDossierError(contract.APS_RUNTIME_FAILURE_DOSSIER_INVALID, "source family mismatch", status_code=500)

    if _as_required_non_negative_int(payload, "total_facts") != sum(int(item.get("total_facts") or 0) for item in source_packets):
        raise ContextDossierError(contract.APS_RUNTIME_FAILURE_DOSSIER_INVALID, "total facts mismatch", status_code=500)
    if _as_required_non_negative_int(payload, "total_caveats") != sum(int(item.get("total_caveats") or 0) for item in source_packets):
        raise ContextDossierError(contract.APS_RUNTIME_FAILURE_DOSSIER_INVALID, "total caveats mismatch", status_code=500)
    if _as_required_non_negative_int(payload, "total_constraints") != sum(int(item.get("total_constraints") or 0) for item in source_packets):
        raise ContextDossierError(contract.APS_RUNTIME_FAILURE_DOSSIER_INVALID, "total constraints mismatch", status_code=500)
    if _as_required_non_negative_int(payload, "total_unresolved_questions") != sum(
        int(item.get("total_unresolved_questions") or 0) for item in source_packets
    ):
        raise ContextDossierError(contract.APS_RUNTIME_FAILURE_DOSSIER_INVALID, "total unresolved questions mismatch", status_code=500)

    expected_dossier_id = contract.derive_context_dossier_id(
        projection_contract_id=str(payload.get("projection_contract_id") or ""),
        fact_grammar_contract_id=str(payload.get("fact_grammar_contract_id") or ""),
        objective=str(payload.get("objective") or ""),
        source_family=str(payload.get("source_family") or ""),
        ordered_source_packets_sha256_value=ordered_digest,
    )
    if str(payload.get("context_dossier_id") or "").strip() != expected_dossier_id:
        raise ContextDossierError(contract.APS_RUNTIME_FAILURE_DOSSIER_INVALID, "context dossier id mismatch", status_code=500)

    checksum = str(payload.get("context_dossier_checksum") or "").strip()
    expected_checksum = contract.compute_context_dossier_checksum(payload)
    if not checksum or checksum != expected_checksum:
        raise ContextDossierError(contract.APS_RUNTIME_FAILURE_DOSSIER_INVALID, "context dossier checksum mismatch", status_code=500)
    return payload


def load_persisted_context_dossier_artifact(
    *,
    context_dossier_id: str | None = None,
    context_dossier_ref: str | Path | None = None,
) -> tuple[dict[str, Any], Path]:
    candidate_path = _resolve_context_dossier_artifact_path(
        context_dossier_id=context_dossier_id,
        context_dossier_ref=context_dossier_ref,
    )
    payload = _read_json(candidate_path)
    if not payload:
        raise ContextDossierError(contract.APS_RUNTIME_FAILURE_DOSSIER_INVALID, "context dossier artifact unreadable", status_code=500)
    validated_payload = _validate_persisted_context_dossier_payload(payload)
    validated_payload["_context_dossier_ref"] = str(candidate_path)
    validated_payload["_persisted"] = True
    return validated_payload, candidate_path


def _conflict_error(message: str, *, inner_code: str | None = None) -> ContextDossierError:
    details = f"{message}: {inner_code}" if inner_code else message
    return ContextDossierError(contract.APS_RUNTIME_FAILURE_CONFLICT, details, status_code=409)


def _persist_or_validate_context_dossier(*, artifact_path: Path, payload: dict[str, Any]) -> tuple[dict[str, Any], str]:
    if artifact_path.exists():
        try:
            existing_payload, existing_path = load_persisted_context_dossier_artifact(context_dossier_ref=artifact_path)
        except ContextDossierError as exc:
            raise _conflict_error(
                "existing persisted context dossier conflicts with derived dossier",
                inner_code=contract.APS_RUNTIME_FAILURE_DOSSIER_INVALID,
            ) from exc
        existing_dossier_id = str(existing_payload.get("context_dossier_id") or "").strip()
        expected_dossier_id = str(payload.get("context_dossier_id") or "").strip()
        if existing_dossier_id != expected_dossier_id:
            raise _conflict_error("existing persisted context dossier id conflicts with derived dossier")
        existing_checksum = str(existing_payload.get("context_dossier_checksum") or "").strip()
        expected_checksum = str(payload.get("context_dossier_checksum") or "").strip()
        if existing_checksum != expected_checksum:
            raise _conflict_error("existing persisted context dossier checksum conflicts with derived dossier")
        if contract.logical_context_dossier_payload(existing_payload) != contract.logical_context_dossier_payload(payload):
            raise _conflict_error("existing persisted context dossier body conflicts with derived dossier")
        return existing_payload, str(existing_path)

    context_dossier_ref = nrc_aps_safeguards.write_json_atomic(artifact_path, payload)
    validated_payload, _validated_path = load_persisted_context_dossier_artifact(context_dossier_ref=context_dossier_ref)
    return validated_payload, context_dossier_ref


def _append_context_dossier_summary(existing: list[dict[str, Any]] | None, entry: dict[str, Any]) -> list[dict[str, Any]]:
    summaries = [dict(item or {}) for item in (existing or []) if isinstance(item, dict)]
    incoming_dossier_id = str(entry.get("context_dossier_id") or "").strip()
    incoming_ref = str(entry.get("ref") or "").strip()
    kept: list[dict[str, Any]] = []
    replaced = False
    for item in summaries:
        same_dossier_id = str(item.get("context_dossier_id") or "").strip() == incoming_dossier_id
        same_ref = incoming_ref and str(item.get("ref") or "").strip() == incoming_ref
        if same_dossier_id or same_ref:
            if not replaced:
                kept.append(dict(entry))
                replaced = True
            continue
        kept.append(item)
    if not replaced:
        kept.append(dict(entry))
    kept.sort(key=lambda item: (str(item.get("context_dossier_id") or ""), str(item.get("ref") or "")))
    return kept


def _candidate_run(db: Session, run_id: str | None) -> ConnectorRun | None:
    normalized_run_id = str(run_id or "").strip()
    if not normalized_run_id:
        return None
    return db.get(ConnectorRun, normalized_run_id)


def _response_payload(payload: dict[str, Any]) -> dict[str, Any]:
    return {
        "schema_id": str(payload.get("schema_id") or contract.APS_CONTEXT_DOSSIER_SCHEMA_ID),
        "schema_version": int(payload.get("schema_version") or contract.APS_CONTEXT_DOSSIER_SCHEMA_VERSION),
        "generated_at_utc": str(payload.get("generated_at_utc") or ""),
        "context_dossier_id": str(payload.get("context_dossier_id") or ""),
        "context_dossier_checksum": str(payload.get("context_dossier_checksum") or ""),
        "context_dossier_ref": str(payload.get("_context_dossier_ref") or "") or None,
        "composition_contract_id": str(
            payload.get("composition_contract_id") or contract.APS_CONTEXT_DOSSIER_COMPOSITION_CONTRACT_ID
        ),
        "dossier_mode": str(payload.get("dossier_mode") or contract.APS_CONTEXT_DOSSIER_MODE),
        "owner_run_id": str(payload.get("owner_run_id") or ""),
        "projection_contract_id": str(payload.get("projection_contract_id") or ""),
        "fact_grammar_contract_id": str(payload.get("fact_grammar_contract_id") or ""),
        "objective": str(payload.get("objective") or ""),
        "source_family": str(payload.get("source_family") or ""),
        "source_packet_count": int(payload.get("source_packet_count") or 0),
        "ordered_source_packets_sha256": str(payload.get("ordered_source_packets_sha256") or ""),
        "total_facts": int(payload.get("total_facts") or 0),
        "total_caveats": int(payload.get("total_caveats") or 0),
        "total_constraints": int(payload.get("total_constraints") or 0),
        "total_unresolved_questions": int(payload.get("total_unresolved_questions") or 0),
        "source_packets": [dict(item or {}) for item in list(payload.get("source_packets") or []) if isinstance(item, dict)],
        "persisted": bool(payload.get("_persisted", False)),
    }


def _resolve_context_packet_payloads(
    normalized_request: dict[str, Any],
) -> tuple[list[dict[str, Any]], list[Path]]:
    source_ids = list(normalized_request.get("context_packet_ids") or [])
    source_refs = list(normalized_request.get("context_packet_refs") or [])
    source_payloads: list[dict[str, Any]] = []
    source_paths: list[Path] = []
    if source_ids:
        raw_values = source_ids
        key_name = "context_packet_id"
    else:
        raw_values = source_refs
        key_name = "context_packet_ref"
    for raw_value in raw_values:
        try:
            payload, source_path = nrc_aps_context_packet.load_persisted_context_packet_artifact(**{key_name: raw_value})
        except nrc_aps_context_packet.ContextPacketError as exc:
            error_code = (
                contract.APS_RUNTIME_FAILURE_SOURCE_PACKET_NOT_FOUND
                if int(exc.status_code) == 404
                else contract.APS_RUNTIME_FAILURE_SOURCE_PACKET_INVALID
            )
            raise ContextDossierError(error_code, str(exc.message), status_code=_status_for_error_code(error_code)) from exc
        try:
            contract.validate_source_packet_compatibility([payload, payload])
        except ValueError:
            raise ContextDossierError(
                contract.APS_RUNTIME_FAILURE_SOURCE_PACKET_INVALID,
                "source packet payload invalid",
                status_code=422,
            ) from None
        source_payloads.append(payload)
        source_paths.append(source_path)
    return source_payloads, source_paths


def _failure_source_locator(normalized_request: dict[str, Any]) -> str:
    context_packet_ids = [str(item).strip() for item in list(normalized_request.get("context_packet_ids") or []) if str(item).strip()]
    context_packet_refs = [
        str(item).strip() for item in list(normalized_request.get("context_packet_refs") or []) if str(item).strip()
    ]
    source_locator = context_packet_ids or context_packet_refs
    return "|".join(source_locator) or "unknown"


def _persist_failure_artifact(
    db: Session,
    *,
    run: ConnectorRun | None,
    owner_run_id: str | None,
    normalized_request: dict[str, Any],
    source_payloads: list[dict[str, Any]] | None,
    error_code: str,
    error_message: str,
    incompatibility_reason: str | None = None,
) -> str | None:
    effective_owner_run_id = str(owner_run_id or getattr(run, "connector_run_id", "") or "").strip()
    if not effective_owner_run_id:
        return None
    failure_context_dossier_id = contract.derive_failure_context_dossier_id(
        source_locator=_failure_source_locator(normalized_request),
        error_code=error_code,
    )
    failure_payload: dict[str, Any] = {
        "schema_id": contract.APS_CONTEXT_DOSSIER_FAILURE_SCHEMA_ID,
        "schema_version": contract.APS_CONTEXT_DOSSIER_SCHEMA_VERSION,
        "generated_at_utc": _utc_iso(),
        "context_dossier_id": failure_context_dossier_id,
        "owner_run_id": effective_owner_run_id,
        "composition_contract_id": contract.APS_CONTEXT_DOSSIER_COMPOSITION_CONTRACT_ID,
        "dossier_mode": contract.APS_CONTEXT_DOSSIER_MODE,
        "source_request": {
            "context_packet_ids": list(normalized_request.get("context_packet_ids") or []),
            "context_packet_refs": list(normalized_request.get("context_packet_refs") or []),
            "persist_dossier": bool(normalized_request.get("persist_dossier", False)),
        },
        "source_packets": [
            {
                "context_packet_id": str(payload.get("context_packet_id") or "").strip() or None,
                "context_packet_checksum": str(payload.get("context_packet_checksum") or "").strip() or None,
                "context_packet_ref": str(payload.get("_context_packet_ref") or payload.get("context_packet_ref") or "").strip() or None,
            }
            for payload in list(source_payloads or [])
            if isinstance(payload, dict)
        ],
        "error_code": str(error_code or contract.APS_RUNTIME_FAILURE_INTERNAL),
        "error_message": str(error_message or ""),
    }
    if str(incompatibility_reason or "").strip():
        failure_payload["incompatibility_reason"] = str(incompatibility_reason or "").strip()
    failure_payload["context_dossier_checksum"] = contract.compute_context_dossier_checksum(failure_payload)
    failure_path = context_dossier_failure_artifact_path(
        owner_run_id=effective_owner_run_id,
        context_dossier_id=failure_context_dossier_id,
        reports_dir=settings.connector_reports_dir,
    )
    failure_ref = nrc_aps_safeguards.write_json_atomic(failure_path, failure_payload)
    if run is None:
        return failure_ref
    existing_refs = dict((run.query_plan_json or {}).get("aps_context_dossier_report_refs") or {})
    failure_refs = [
        str(item).strip()
        for item in list(existing_refs.get("aps_context_dossier_failures") or [])
        if str(item).strip()
    ]
    if failure_ref not in failure_refs:
        failure_refs.append(failure_ref)
    run.query_plan_json = {
        **(run.query_plan_json or {}),
        "aps_context_dossier_report_refs": {
            "aps_context_dossiers": [
                str(item).strip()
                for item in list(existing_refs.get("aps_context_dossiers") or [])
                if str(item).strip()
            ],
            "aps_context_dossier_failures": failure_refs,
        },
    }
    db.commit()
    return failure_ref


def assemble_context_dossier(db: Session, *, request_payload: dict[str, Any]) -> dict[str, Any]:
    try:
        normalized_request = contract.normalize_request_payload(request_payload)
    except ValueError as exc:
        code = str(exc) or contract.APS_RUNTIME_FAILURE_INVALID_REQUEST
        raise ContextDossierError(code, f"invalid request: {code}", status_code=_status_for_error_code(code)) from None

    persist_dossier = bool(normalized_request.get("persist_dossier", False))
    source_payloads: list[dict[str, Any]] = []
    run: ConnectorRun | None = None
    owner_run_id: str | None = None
    incompatibility_reason: str | None = None
    try:
        source_payloads, _source_paths = _resolve_context_packet_payloads(normalized_request)
        if source_payloads:
            first_source_descriptor = dict(dict(source_payloads[0] or {}).get("source_descriptor") or {})
            owner_run_id = str(first_source_descriptor.get("owner_run_id") or "").strip() or None
            run = _candidate_run(db, owner_run_id)
        try:
            context_dossier_payload = contract.build_context_dossier_payload(
                source_payloads,
                generated_at_utc=_utc_iso(),
            )
        except ValueError as exc:
            code, incompatibility_reason = _parse_incompatibility_or_error_code(str(exc))
            if code == contract.APS_RUNTIME_FAILURE_SOURCE_PACKET_INCOMPATIBLE and not incompatibility_reason:
                incompatibility_reason = contract.APS_RUNTIME_INCOMPAT_REASON_SOURCE_FAMILY
            raise ContextDossierError(code, f"context dossier composition failed: {code}", status_code=_status_for_error_code(code)) from None

        owner_run_id = str(context_dossier_payload.get("owner_run_id") or "").strip() or owner_run_id
        run = _candidate_run(db, owner_run_id)
        if persist_dossier:
            artifact_path = context_dossier_artifact_path(
                owner_run_id=str(owner_run_id or ""),
                context_dossier_id=str(context_dossier_payload.get("context_dossier_id") or ""),
                reports_dir=settings.connector_reports_dir,
            )
            context_dossier_payload, context_dossier_ref = _persist_or_validate_context_dossier(
                artifact_path=artifact_path,
                payload=context_dossier_payload,
            )
            if run is not None:
                existing_refs = dict((run.query_plan_json or {}).get("aps_context_dossier_report_refs") or {})
                dossier_refs = [
                    str(item).strip()
                    for item in list(existing_refs.get("aps_context_dossiers") or [])
                    if str(item).strip()
                ]
                if context_dossier_ref not in dossier_refs:
                    dossier_refs.append(context_dossier_ref)
                failure_refs = [
                    str(item).strip()
                    for item in list(existing_refs.get("aps_context_dossier_failures") or [])
                    if str(item).strip()
                ]
                summaries = _append_context_dossier_summary(
                    (run.query_plan_json or {}).get("aps_context_dossier_summaries"),
                    {
                        "context_dossier_id": str(context_dossier_payload.get("context_dossier_id") or ""),
                        "context_dossier_checksum": str(context_dossier_payload.get("context_dossier_checksum") or ""),
                        "dossier_mode": str(context_dossier_payload.get("dossier_mode") or ""),
                        "owner_run_id": str(context_dossier_payload.get("owner_run_id") or ""),
                        "projection_contract_id": str(context_dossier_payload.get("projection_contract_id") or ""),
                        "fact_grammar_contract_id": str(context_dossier_payload.get("fact_grammar_contract_id") or ""),
                        "objective": str(context_dossier_payload.get("objective") or ""),
                        "source_family": str(context_dossier_payload.get("source_family") or ""),
                        "source_packet_count": int(context_dossier_payload.get("source_packet_count") or 0),
                        "ordered_source_packets_sha256": str(context_dossier_payload.get("ordered_source_packets_sha256") or ""),
                        "total_facts": int(context_dossier_payload.get("total_facts") or 0),
                        "total_caveats": int(context_dossier_payload.get("total_caveats") or 0),
                        "total_constraints": int(context_dossier_payload.get("total_constraints") or 0),
                        "total_unresolved_questions": int(context_dossier_payload.get("total_unresolved_questions") or 0),
                        "ref": context_dossier_ref,
                    },
                )
                run.query_plan_json = {
                    **(run.query_plan_json or {}),
                    "aps_context_dossier_report_refs": {
                        "aps_context_dossiers": dossier_refs,
                        "aps_context_dossier_failures": failure_refs,
                    },
                    "aps_context_dossier_summaries": summaries,
                }
                db.commit()
            context_dossier_payload["_context_dossier_ref"] = context_dossier_ref
            context_dossier_payload["_persisted"] = True
        else:
            context_dossier_payload["_context_dossier_ref"] = None
            context_dossier_payload["_persisted"] = False
        return _response_payload(context_dossier_payload)
    except ContextDossierError as exc:
        if persist_dossier:
            _persist_failure_artifact(
                db,
                run=run,
                owner_run_id=owner_run_id,
                normalized_request=normalized_request,
                source_payloads=source_payloads,
                error_code=exc.code,
                error_message=exc.message,
                incompatibility_reason=incompatibility_reason,
            )
        raise
    except Exception as exc:  # noqa: BLE001
        if persist_dossier:
            _persist_failure_artifact(
                db,
                run=run,
                owner_run_id=owner_run_id,
                normalized_request=normalized_request,
                source_payloads=source_payloads,
                error_code=contract.APS_RUNTIME_FAILURE_INTERNAL,
                error_message=str(exc),
                incompatibility_reason=incompatibility_reason,
            )
        raise ContextDossierError(contract.APS_RUNTIME_FAILURE_INTERNAL, str(exc), status_code=500) from exc


def get_persisted_context_dossier(*, context_dossier_id: str) -> dict[str, Any]:
    payload, _candidate_path = load_persisted_context_dossier_artifact(
        context_dossier_id=str(context_dossier_id or "").strip()
    )
    return _response_payload(payload)
