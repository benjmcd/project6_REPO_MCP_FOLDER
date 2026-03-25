from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from sqlalchemy.orm import Session

from app.core.config import settings
from app.models import ConnectorRun
from app.services import nrc_aps_context_packet_contract as contract
from app.services import nrc_aps_evidence_report
from app.services import nrc_aps_evidence_report_export
from app.services import nrc_aps_evidence_report_export_package
from app.services import nrc_aps_safeguards


class ContextPacketError(RuntimeError):
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


def context_packet_artifact_path(
    *,
    owner_run_id: str,
    context_packet_id: str,
    reports_dir: str | Path,
) -> Path:
    scope = f"run_{_safe_scope_token(owner_run_id)}"
    return Path(reports_dir) / contract.expected_context_packet_file_name(scope=scope, context_packet_id=context_packet_id)


def context_packet_failure_artifact_path(
    *,
    owner_run_id: str,
    context_packet_id: str,
    reports_dir: str | Path,
) -> Path:
    scope = f"run_{_safe_scope_token(owner_run_id)}"
    return Path(reports_dir) / contract.expected_failure_file_name(scope=scope, context_packet_id=context_packet_id)


def find_context_packet_artifact_by_id(*, context_packet_id: str, reports_dir: str | Path) -> Path | None:
    pattern = f"*_{contract.artifact_id_token(context_packet_id)}_aps_context_packet_v1.json"
    candidates = sorted(Path(reports_dir).glob(pattern), key=lambda path: path.name)
    if not candidates:
        return None
    return candidates[0]


def _resolve_context_packet_artifact_path(
    *,
    context_packet_id: str | None = None,
    context_packet_ref: str | Path | None = None,
) -> Path:
    normalized_context_packet_id = str(context_packet_id or "").strip()
    normalized_context_packet_ref = str(context_packet_ref or "").strip()
    if bool(normalized_context_packet_id) == bool(normalized_context_packet_ref):
        raise ContextPacketError(
            contract.APS_RUNTIME_FAILURE_INVALID_REQUEST,
            "exactly one of context_packet_id or context_packet_ref is required",
            status_code=400,
        )
    if normalized_context_packet_ref:
        candidate_path = Path(normalized_context_packet_ref)
    else:
        candidate_path = find_context_packet_artifact_by_id(
            context_packet_id=normalized_context_packet_id,
            reports_dir=settings.connector_reports_dir,
        )
        if candidate_path is None:
            raise ContextPacketError(
                contract.APS_RUNTIME_FAILURE_NOT_FOUND,
                "context packet not found",
                status_code=404,
            )
    if not candidate_path.exists():
        raise ContextPacketError(
            contract.APS_RUNTIME_FAILURE_NOT_FOUND,
            "context packet not found",
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


def _validate_failure_payload_schema(payload: dict[str, Any]) -> dict[str, Any]:
    if str(payload.get("schema_id") or "") != contract.APS_CONTEXT_PACKET_FAILURE_SCHEMA_ID:
        raise ContextPacketError(
            contract.APS_RUNTIME_FAILURE_INVALID,
            "context packet failure schema mismatch",
            status_code=500,
        )
    if int(payload.get("schema_version") or 0) != contract.APS_CONTEXT_PACKET_SCHEMA_VERSION:
        raise ContextPacketError(
            contract.APS_RUNTIME_FAILURE_INVALID,
            "context packet failure schema version mismatch",
            status_code=500,
        )
    if str(payload.get("projection_contract_id") or "") != contract.APS_CONTEXT_PACKET_PROJECTION_CONTRACT_ID:
        raise ContextPacketError(
            contract.APS_RUNTIME_FAILURE_INVALID,
            "projection contract mismatch",
            status_code=500,
        )
    if str(payload.get("fact_grammar_contract_id") or "") != contract.APS_CONTEXT_PACKET_FACT_GRAMMAR_CONTRACT_ID:
        raise ContextPacketError(
            contract.APS_RUNTIME_FAILURE_INVALID,
            "fact grammar contract mismatch",
            status_code=500,
        )
    checksum = str(payload.get("context_packet_checksum") or "").strip()
    expected_checksum = contract.compute_context_packet_checksum(payload)
    if not checksum or checksum != expected_checksum:
        raise ContextPacketError(
            contract.APS_RUNTIME_FAILURE_INVALID,
            "context packet failure checksum mismatch",
            status_code=500,
        )
    return payload


def _validate_note_rows(
    rows: list[dict[str, Any]],
    *,
    ordinal_field: str,
) -> list[dict[str, Any]]:
    normalized = [dict(item or {}) for item in rows if isinstance(item, dict)]
    for index, row in enumerate(normalized, start=1):
        if int(row.get(ordinal_field) or 0) != index:
            raise ContextPacketError(
                contract.APS_RUNTIME_FAILURE_INVALID,
                f"{ordinal_field} mismatch",
                status_code=500,
            )
    return normalized


def _validate_persisted_context_packet_payload(payload: dict[str, Any]) -> dict[str, Any]:
    if str(payload.get("schema_id") or "") != contract.APS_CONTEXT_PACKET_SCHEMA_ID:
        raise ContextPacketError(contract.APS_RUNTIME_FAILURE_INVALID, "context packet schema mismatch", status_code=500)
    if int(payload.get("schema_version") or 0) != contract.APS_CONTEXT_PACKET_SCHEMA_VERSION:
        raise ContextPacketError(contract.APS_RUNTIME_FAILURE_INVALID, "context packet schema version mismatch", status_code=500)
    if str(payload.get("projection_contract_id") or "") != contract.APS_CONTEXT_PACKET_PROJECTION_CONTRACT_ID:
        raise ContextPacketError(contract.APS_RUNTIME_FAILURE_INVALID, "projection contract mismatch", status_code=500)
    if str(payload.get("fact_grammar_contract_id") or "") != contract.APS_CONTEXT_PACKET_FACT_GRAMMAR_CONTRACT_ID:
        raise ContextPacketError(contract.APS_RUNTIME_FAILURE_INVALID, "fact grammar contract mismatch", status_code=500)
    source_family = str(payload.get("source_family") or "")
    if source_family not in contract.APS_CONTEXT_PACKET_ALLOWED_SOURCE_FAMILIES:
        raise ContextPacketError(contract.APS_RUNTIME_FAILURE_INVALID, "source family mismatch", status_code=500)
    source_descriptor = dict(payload.get("source_descriptor") or {})
    if str(source_descriptor.get("source_family") or "") != source_family:
        raise ContextPacketError(contract.APS_RUNTIME_FAILURE_INVALID, "source descriptor family mismatch", status_code=500)

    source_id = str(source_descriptor.get("source_id") or "").strip()
    source_checksum = str(source_descriptor.get("source_checksum") or "").strip()
    if not source_id or not source_checksum:
        raise ContextPacketError(contract.APS_RUNTIME_FAILURE_INVALID, "source descriptor missing id or checksum", status_code=500)

    expected_context_packet_id = contract.derive_context_packet_id(
        source_family=source_family,
        source_id=source_id,
        source_checksum=source_checksum,
    )
    if str(payload.get("context_packet_id") or "").strip() != expected_context_packet_id:
        raise ContextPacketError(contract.APS_RUNTIME_FAILURE_INVALID, "context packet id mismatch", status_code=500)

    facts = [dict(item or {}) for item in list(payload.get("facts") or []) if isinstance(item, dict)]
    for index, fact in enumerate(facts, start=1):
        if int(fact.get("fact_ordinal") or 0) != index:
            raise ContextPacketError(contract.APS_RUNTIME_FAILURE_INVALID, "fact ordinal mismatch", status_code=500)
    caveats = _validate_note_rows(
        [dict(item or {}) for item in list(payload.get("caveats") or []) if isinstance(item, dict)],
        ordinal_field="caveat_ordinal",
    )
    constraints = _validate_note_rows(
        [dict(item or {}) for item in list(payload.get("constraints") or []) if isinstance(item, dict)],
        ordinal_field="constraint_ordinal",
    )
    unresolved_questions = _validate_note_rows(
        [dict(item or {}) for item in list(payload.get("unresolved_questions") or []) if isinstance(item, dict)],
        ordinal_field="unresolved_question_ordinal",
    )
    if int(payload.get("total_facts") or 0) != len(facts):
        raise ContextPacketError(contract.APS_RUNTIME_FAILURE_INVALID, "total facts mismatch", status_code=500)
    if int(payload.get("total_caveats") or 0) != len(caveats):
        raise ContextPacketError(contract.APS_RUNTIME_FAILURE_INVALID, "total caveats mismatch", status_code=500)
    if int(payload.get("total_constraints") or 0) != len(constraints):
        raise ContextPacketError(contract.APS_RUNTIME_FAILURE_INVALID, "total constraints mismatch", status_code=500)
    if int(payload.get("total_unresolved_questions") or 0) != len(unresolved_questions):
        raise ContextPacketError(contract.APS_RUNTIME_FAILURE_INVALID, "total unresolved questions mismatch", status_code=500)
    checksum = str(payload.get("context_packet_checksum") or "").strip()
    expected_checksum = contract.compute_context_packet_checksum(payload)
    if not checksum or checksum != expected_checksum:
        raise ContextPacketError(contract.APS_RUNTIME_FAILURE_WRITE_FAILED, "context packet checksum mismatch", status_code=500)
    return payload


def load_persisted_context_packet_artifact(
    *,
    context_packet_id: str | None = None,
    context_packet_ref: str | Path | None = None,
) -> tuple[dict[str, Any], Path]:
    candidate_path = _resolve_context_packet_artifact_path(
        context_packet_id=context_packet_id,
        context_packet_ref=context_packet_ref,
    )
    payload = _read_json(candidate_path)
    if not payload:
        raise ContextPacketError(contract.APS_RUNTIME_FAILURE_INVALID, "context packet artifact unreadable", status_code=500)
    validated_payload = _validate_persisted_context_packet_payload(payload)
    validated_payload["_context_packet_ref"] = str(candidate_path)
    validated_payload["_persisted"] = True
    return validated_payload, candidate_path


def _conflict_error(message: str, *, inner_code: str | None = None) -> ContextPacketError:
    details = f"{message}: {inner_code}" if inner_code else message
    return ContextPacketError(contract.APS_RUNTIME_FAILURE_CONFLICT, details, status_code=409)


def _persist_or_validate_context_packet(*, artifact_path: Path, payload: dict[str, Any]) -> tuple[dict[str, Any], str]:
    if artifact_path.exists():
        try:
            existing_payload, existing_path = load_persisted_context_packet_artifact(context_packet_ref=artifact_path)
        except ContextPacketError as exc:
            raise _conflict_error("existing persisted context packet conflicts with derived packet", inner_code=exc.code) from exc

        existing_packet_id = str(existing_payload.get("context_packet_id") or "").strip()
        expected_packet_id = str(payload.get("context_packet_id") or "").strip()
        if existing_packet_id != expected_packet_id:
            raise _conflict_error("existing persisted context packet id conflicts with derived packet")
        existing_checksum = str(existing_payload.get("context_packet_checksum") or "").strip()
        expected_checksum = str(payload.get("context_packet_checksum") or "").strip()
        if existing_checksum != expected_checksum:
            raise _conflict_error("existing persisted context packet checksum conflicts with derived packet")
        if contract.logical_context_packet_payload(existing_payload) != contract.logical_context_packet_payload(payload):
            raise _conflict_error("existing persisted context packet body conflicts with derived packet")
        return existing_payload, str(existing_path)

    context_packet_ref = nrc_aps_safeguards.write_json_atomic(artifact_path, payload)
    validated_payload, _validated_path = load_persisted_context_packet_artifact(context_packet_ref=context_packet_ref)
    return validated_payload, context_packet_ref


def _append_context_packet_summary(existing: list[dict[str, Any]] | None, entry: dict[str, Any]) -> list[dict[str, Any]]:
    summaries = [dict(item or {}) for item in (existing or []) if isinstance(item, dict)]
    incoming_packet_id = str(entry.get("context_packet_id") or "").strip()
    incoming_ref = str(entry.get("ref") or "").strip()
    kept: list[dict[str, Any]] = []
    replaced = False
    for item in summaries:
        same_packet_id = str(item.get("context_packet_id") or "").strip() == incoming_packet_id
        same_ref = incoming_ref and str(item.get("ref") or "").strip() == incoming_ref
        if same_packet_id or same_ref:
            if not replaced:
                kept.append(dict(entry))
                replaced = True
            continue
        kept.append(item)
    if not replaced:
        kept.append(dict(entry))
    kept.sort(key=lambda item: (str(item.get("context_packet_id") or ""), str(item.get("ref") or "")))
    return kept


def _candidate_run(db: Session, run_id: str | None) -> ConnectorRun | None:
    normalized_run_id = str(run_id or "").strip()
    if not normalized_run_id:
        return None
    return db.get(ConnectorRun, normalized_run_id)


def _response_payload(payload: dict[str, Any]) -> dict[str, Any]:
    return {
        "schema_id": str(payload.get("schema_id") or contract.APS_CONTEXT_PACKET_SCHEMA_ID),
        "schema_version": int(payload.get("schema_version") or contract.APS_CONTEXT_PACKET_SCHEMA_VERSION),
        "generated_at_utc": str(payload.get("generated_at_utc") or ""),
        "context_packet_id": str(payload.get("context_packet_id") or ""),
        "context_packet_checksum": str(payload.get("context_packet_checksum") or ""),
        "context_packet_ref": str(payload.get("_context_packet_ref") or "") or None,
        "projection_contract_id": str(payload.get("projection_contract_id") or contract.APS_CONTEXT_PACKET_PROJECTION_CONTRACT_ID),
        "fact_grammar_contract_id": str(payload.get("fact_grammar_contract_id") or contract.APS_CONTEXT_PACKET_FACT_GRAMMAR_CONTRACT_ID),
        "source_family": str(payload.get("source_family") or ""),
        "source_descriptor": dict(payload.get("source_descriptor") or {}),
        "objective": str(payload.get("objective") or contract.APS_CONTEXT_PACKET_OBJECTIVE),
        "scope": dict(payload.get("scope") or {}),
        "facts": [dict(item or {}) for item in list(payload.get("facts") or []) if isinstance(item, dict)],
        "caveats": [dict(item or {}) for item in list(payload.get("caveats") or []) if isinstance(item, dict)],
        "constraints": [dict(item or {}) for item in list(payload.get("constraints") or []) if isinstance(item, dict)],
        "unresolved_questions": [
            dict(item or {}) for item in list(payload.get("unresolved_questions") or []) if isinstance(item, dict)
        ],
        "total_facts": int(payload.get("total_facts") or 0),
        "total_caveats": int(payload.get("total_caveats") or 0),
        "total_constraints": int(payload.get("total_constraints") or 0),
        "total_unresolved_questions": int(payload.get("total_unresolved_questions") or 0),
        "persisted": bool(payload.get("_persisted", False)),
    }


def _resolve_source_payload(
    normalized_request: dict[str, Any],
) -> tuple[dict[str, Any], Path]:
    source_family = str(normalized_request.get("source_family") or "")
    if source_family == contract.APS_CONTEXT_PACKET_SOURCE_FAMILY_REPORT:
        try:
            return nrc_aps_evidence_report.load_persisted_evidence_report_artifact(
                evidence_report_id=normalized_request.get("evidence_report_id"),
                evidence_report_ref=normalized_request.get("evidence_report_ref"),
            )
        except nrc_aps_evidence_report.EvidenceReportError as exc:
            error_code = contract.APS_RUNTIME_FAILURE_SOURCE_NOT_FOUND if int(exc.status_code) == 404 else contract.APS_RUNTIME_FAILURE_SOURCE_INVALID
            status_code = 404 if error_code == contract.APS_RUNTIME_FAILURE_SOURCE_NOT_FOUND else 422
            raise ContextPacketError(error_code, str(exc.message), status_code=status_code) from exc

    if source_family == contract.APS_CONTEXT_PACKET_SOURCE_FAMILY_EXPORT:
        try:
            return nrc_aps_evidence_report_export.load_persisted_evidence_report_export_artifact(
                evidence_report_export_id=normalized_request.get("evidence_report_export_id"),
                evidence_report_export_ref=normalized_request.get("evidence_report_export_ref"),
            )
        except nrc_aps_evidence_report_export.EvidenceReportExportError as exc:
            error_code = contract.APS_RUNTIME_FAILURE_SOURCE_NOT_FOUND if int(exc.status_code) == 404 else contract.APS_RUNTIME_FAILURE_SOURCE_INVALID
            status_code = 404 if error_code == contract.APS_RUNTIME_FAILURE_SOURCE_NOT_FOUND else 422
            raise ContextPacketError(error_code, str(exc.message), status_code=status_code) from exc

    if source_family == contract.APS_CONTEXT_PACKET_SOURCE_FAMILY_PACKAGE:
        try:
            return nrc_aps_evidence_report_export_package.load_persisted_evidence_report_export_package_artifact(
                evidence_report_export_package_id=normalized_request.get("evidence_report_export_package_id"),
                evidence_report_export_package_ref=normalized_request.get("evidence_report_export_package_ref"),
            )
        except nrc_aps_evidence_report_export_package.EvidenceReportExportPackageError as exc:
            error_code = contract.APS_RUNTIME_FAILURE_SOURCE_NOT_FOUND if int(exc.status_code) == 404 else contract.APS_RUNTIME_FAILURE_SOURCE_INVALID
            status_code = 404 if error_code == contract.APS_RUNTIME_FAILURE_SOURCE_NOT_FOUND else 422
            raise ContextPacketError(error_code, str(exc.message), status_code=status_code) from exc

    raise ContextPacketError(contract.APS_RUNTIME_FAILURE_INVALID_REQUEST, "invalid source family", status_code=422)


def _failure_source_locator(normalized_request: dict[str, Any]) -> str:
    source_family = str(normalized_request.get("source_family") or "")
    if source_family == contract.APS_CONTEXT_PACKET_SOURCE_FAMILY_REPORT:
        return (
            str(normalized_request.get("evidence_report_id") or "").strip()
            or str(normalized_request.get("evidence_report_ref") or "").strip()
            or "unknown"
        )
    if source_family == contract.APS_CONTEXT_PACKET_SOURCE_FAMILY_EXPORT:
        return (
            str(normalized_request.get("evidence_report_export_id") or "").strip()
            or str(normalized_request.get("evidence_report_export_ref") or "").strip()
            or "unknown"
        )
    if source_family == contract.APS_CONTEXT_PACKET_SOURCE_FAMILY_PACKAGE:
        return (
            str(normalized_request.get("evidence_report_export_package_id") or "").strip()
            or str(normalized_request.get("evidence_report_export_package_ref") or "").strip()
            or "unknown"
        )
    return "unknown"


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
    source_family = str(normalized_request.get("source_family") or "")
    source_descriptor = (
        contract.source_descriptor_payload(source_family, dict(source_payload or {}))
        if isinstance(source_payload, dict) and source_family in contract.APS_CONTEXT_PACKET_ALLOWED_SOURCE_FAMILIES
        else {}
    )
    failure_context_packet_id = contract.derive_failure_context_packet_id(
        source_locator=_failure_source_locator(normalized_request),
        error_code=error_code,
    )
    failure_payload = {
        "schema_id": contract.APS_CONTEXT_PACKET_FAILURE_SCHEMA_ID,
        "schema_version": contract.APS_CONTEXT_PACKET_SCHEMA_VERSION,
        "generated_at_utc": _utc_iso(),
        "context_packet_id": failure_context_packet_id,
        "projection_contract_id": contract.APS_CONTEXT_PACKET_PROJECTION_CONTRACT_ID,
        "fact_grammar_contract_id": contract.APS_CONTEXT_PACKET_FACT_GRAMMAR_CONTRACT_ID,
        "owner_run_id": effective_owner_run_id,
        "source_family": source_family,
        "source_request": {
            "source_family": source_family,
            "evidence_report_id": normalized_request.get("evidence_report_id"),
            "evidence_report_ref": normalized_request.get("evidence_report_ref"),
            "evidence_report_export_id": normalized_request.get("evidence_report_export_id"),
            "evidence_report_export_ref": normalized_request.get("evidence_report_export_ref"),
            "evidence_report_export_package_id": normalized_request.get("evidence_report_export_package_id"),
            "evidence_report_export_package_ref": normalized_request.get("evidence_report_export_package_ref"),
            "persist_context_packet": bool(normalized_request.get("persist_context_packet", False)),
        },
        "source_descriptor": source_descriptor,
        "error_code": str(error_code or contract.APS_RUNTIME_FAILURE_INTERNAL),
        "error_message": str(error_message or ""),
    }
    failure_payload["context_packet_checksum"] = contract.compute_context_packet_checksum(failure_payload)
    failure_path = context_packet_failure_artifact_path(
        owner_run_id=effective_owner_run_id,
        context_packet_id=failure_context_packet_id,
        reports_dir=settings.connector_reports_dir,
    )
    failure_ref = nrc_aps_safeguards.write_json_atomic(failure_path, failure_payload)
    if run is None:
        return failure_ref
    existing_refs = dict((run.query_plan_json or {}).get("aps_context_packet_report_refs") or {})
    failure_refs = [
        str(item).strip()
        for item in list(existing_refs.get("aps_context_packet_failures") or [])
        if str(item).strip()
    ]
    if failure_ref not in failure_refs:
        failure_refs.append(failure_ref)
    run.query_plan_json = {
        **(run.query_plan_json or {}),
        "aps_context_packet_report_refs": {
            "aps_context_packets": [
                str(item).strip() for item in list(existing_refs.get("aps_context_packets") or []) if str(item).strip()
            ],
            "aps_context_packet_failures": failure_refs,
        },
    }
    db.commit()
    return failure_ref


def assemble_context_packet(
    db: Session,
    *,
    request_payload: dict[str, Any],
) -> dict[str, Any]:
    try:
        normalized_request = contract.normalize_request_payload(request_payload)
    except ValueError as exc:
        code = str(exc) or contract.APS_RUNTIME_FAILURE_INVALID_REQUEST
        raise ContextPacketError(code, f"invalid request: {code}", status_code=422) from None

    persist_context_packet = bool(normalized_request.get("persist_context_packet", False))
    source_payload: dict[str, Any] | None = None
    run: ConnectorRun | None = None
    owner_run_id: str | None = None
    try:
        source_payload, _source_path = _resolve_source_payload(normalized_request)
        source_family = str(normalized_request.get("source_family") or "")
        source_descriptor = contract.source_descriptor_payload(source_family, source_payload)
        owner_run_id = str(source_descriptor.get("owner_run_id") or "").strip() or None
        if not owner_run_id:
            raise ContextPacketError(
                contract.APS_RUNTIME_FAILURE_SOURCE_INVALID,
                "source artifact missing owner run id",
                status_code=422,
            )
        run = _candidate_run(db, owner_run_id)

        context_packet_payload = contract.build_context_packet_payload(
            source_family=source_family,
            source_payload=source_payload,
            generated_at_utc=_utc_iso(),
        )
        if persist_context_packet:
            artifact_path = context_packet_artifact_path(
                owner_run_id=owner_run_id,
                context_packet_id=str(context_packet_payload.get("context_packet_id") or ""),
                reports_dir=settings.connector_reports_dir,
            )
            context_packet_payload, context_packet_ref = _persist_or_validate_context_packet(
                artifact_path=artifact_path,
                payload=context_packet_payload,
            )
            if run is not None:
                existing_refs = dict((run.query_plan_json or {}).get("aps_context_packet_report_refs") or {})
                context_packet_refs = [
                    str(item).strip() for item in list(existing_refs.get("aps_context_packets") or []) if str(item).strip()
                ]
                if context_packet_ref not in context_packet_refs:
                    context_packet_refs.append(context_packet_ref)
                failure_refs = [
                    str(item).strip()
                    for item in list(existing_refs.get("aps_context_packet_failures") or [])
                    if str(item).strip()
                ]
                summaries = _append_context_packet_summary(
                    (run.query_plan_json or {}).get("aps_context_packet_summaries"),
                    {
                        "context_packet_id": str(context_packet_payload.get("context_packet_id") or ""),
                        "context_packet_checksum": str(context_packet_payload.get("context_packet_checksum") or ""),
                        "source_family": str(context_packet_payload.get("source_family") or ""),
                        "source_id": str(dict(context_packet_payload.get("source_descriptor") or {}).get("source_id") or ""),
                        "source_checksum": str(
                            dict(context_packet_payload.get("source_descriptor") or {}).get("source_checksum") or ""
                        ),
                        "owner_run_id": str(dict(context_packet_payload.get("source_descriptor") or {}).get("owner_run_id") or ""),
                        "total_facts": int(context_packet_payload.get("total_facts") or 0),
                        "total_caveats": int(context_packet_payload.get("total_caveats") or 0),
                        "total_constraints": int(context_packet_payload.get("total_constraints") or 0),
                        "total_unresolved_questions": int(context_packet_payload.get("total_unresolved_questions") or 0),
                        "ref": context_packet_ref,
                    },
                )
                run.query_plan_json = {
                    **(run.query_plan_json or {}),
                    "aps_context_packet_report_refs": {
                        "aps_context_packets": context_packet_refs,
                        "aps_context_packet_failures": failure_refs,
                    },
                    "aps_context_packet_summaries": summaries,
                }
                db.commit()
            context_packet_payload["_context_packet_ref"] = context_packet_ref
            context_packet_payload["_persisted"] = True
        else:
            context_packet_payload["_context_packet_ref"] = None
            context_packet_payload["_persisted"] = False
        return _response_payload(context_packet_payload)
    except ContextPacketError as exc:
        if persist_context_packet:
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
        if persist_context_packet:
            _persist_failure_artifact(
                db,
                run=run,
                owner_run_id=owner_run_id,
                normalized_request=normalized_request,
                source_payload=source_payload,
                error_code=contract.APS_RUNTIME_FAILURE_INTERNAL,
                error_message=str(exc),
            )
        raise ContextPacketError(contract.APS_RUNTIME_FAILURE_INTERNAL, str(exc), status_code=500) from exc


def get_persisted_context_packet(*, context_packet_id: str) -> dict[str, Any]:
    payload, _candidate_path = load_persisted_context_packet_artifact(
        context_packet_id=str(context_packet_id or "").strip()
    )
    return _response_payload(payload)
