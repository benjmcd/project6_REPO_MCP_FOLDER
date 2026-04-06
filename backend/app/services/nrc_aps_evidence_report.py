from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from sqlalchemy.orm import Session

from app.core.config import settings
from app.models import ConnectorRun
from app.services import nrc_aps_evidence_citation_pack
from app.services import nrc_aps_evidence_report_contract as contract
from app.services import nrc_aps_safeguards
from app.services.review_nrc_aps_runtime import connector_run_is_baseline_visible


class EvidenceReportError(RuntimeError):
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


def evidence_report_artifact_path(*, run_id: str, evidence_report_id: str, reports_dir: str | Path) -> Path:
    scope = f"run_{_safe_scope_token(run_id)}"
    return Path(reports_dir) / contract.expected_report_file_name(scope=scope, evidence_report_id=evidence_report_id)


def evidence_report_failure_artifact_path(*, run_id: str, evidence_report_id: str, reports_dir: str | Path) -> Path:
    scope = f"run_{_safe_scope_token(run_id)}"
    return Path(reports_dir) / contract.expected_failure_file_name(scope=scope, evidence_report_id=evidence_report_id)


def find_evidence_report_artifact_by_id(*, evidence_report_id: str, reports_dir: str | Path) -> Path | None:
    pattern = f"*_{contract.artifact_id_token(evidence_report_id)}_aps_evidence_report_v1.json"
    candidates = sorted(Path(reports_dir).glob(pattern), key=lambda path: path.name)
    if not candidates:
        return None
    return candidates[0]


def _resolve_evidence_report_artifact_path(
    *,
    evidence_report_id: str | None = None,
    evidence_report_ref: str | Path | None = None,
) -> Path:
    normalized_report_id = str(evidence_report_id or "").strip()
    normalized_report_ref = str(evidence_report_ref or "").strip()
    if bool(normalized_report_id) == bool(normalized_report_ref):
        raise EvidenceReportError(contract.APS_RUNTIME_FAILURE_INVALID_REQUEST, "exactly one of evidence_report_id or evidence_report_ref is required", status_code=400)
    if normalized_report_ref:
        candidate_path = Path(normalized_report_ref)
    else:
        candidate_path = find_evidence_report_artifact_by_id(evidence_report_id=normalized_report_id, reports_dir=settings.connector_reports_dir)
        if candidate_path is None:
            raise EvidenceReportError(contract.APS_RUNTIME_FAILURE_REPORT_NOT_FOUND, "evidence report not found", status_code=404)
    if not candidate_path.exists():
        raise EvidenceReportError(contract.APS_RUNTIME_FAILURE_REPORT_NOT_FOUND, "evidence report not found", status_code=404)
    return candidate_path


def resolve_persisted_evidence_report_artifact_path(
    *,
    evidence_report_id: str | None = None,
    evidence_report_ref: str | Path | None = None,
) -> Path:
    return _resolve_evidence_report_artifact_path(
        evidence_report_id=evidence_report_id,
        evidence_report_ref=evidence_report_ref,
    )


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


def read_persisted_evidence_report_artifact_json(path: str | Path | None) -> dict[str, Any]:
    return _read_json(path)


def _validate_section_rows(payload: dict[str, Any]) -> None:
    sections = [dict(item or {}) for item in list(payload.get("sections") or []) if isinstance(item, dict)]
    if int(payload.get("total_sections") or 0) != len(sections):
        raise EvidenceReportError(contract.APS_RUNTIME_FAILURE_SOURCE_CITATION_PACK_INVALID, "section count mismatch", status_code=500)
    if int(payload.get("total_groups") or 0) != len({str(item.get("group_id") or "") for item in sections}):
        raise EvidenceReportError(contract.APS_RUNTIME_FAILURE_SOURCE_CITATION_PACK_INVALID, "group count mismatch", status_code=500)
    total_citations = 0
    first_ordinals: list[int] = []
    source_pack = dict(payload.get("source_citation_pack") or {})
    source_pack_id = str(source_pack.get("citation_pack_id") or "")
    source_pack_checksum = str(source_pack.get("citation_pack_checksum") or "")
    for index, section in enumerate(sections, start=1):
        if int(section.get("section_ordinal") or 0) != index:
            raise EvidenceReportError(contract.APS_RUNTIME_FAILURE_SOURCE_CITATION_PACK_INVALID, "section ordinal mismatch", status_code=500)
        if str(section.get("section_type") or "") != contract.APS_REPORT_SECTION_TYPE:
            raise EvidenceReportError(contract.APS_RUNTIME_FAILURE_SOURCE_CITATION_PACK_INVALID, "section type mismatch", status_code=500)
        expected_title = contract.section_title(
            section_ordinal=index,
            accession_number=section.get("accession_number"),
            content_id=section.get("content_id"),
        )
        if str(section.get("title") or "") != expected_title:
            raise EvidenceReportError(contract.APS_RUNTIME_FAILURE_SOURCE_CITATION_PACK_INVALID, "section title mismatch", status_code=500)
        expected_section_id = contract.derive_section_id(
            citation_pack_id=source_pack_id,
            citation_pack_checksum=source_pack_checksum,
            group_id=str(section.get("group_id") or ""),
        )
        if str(section.get("section_id") or "") != expected_section_id:
            raise EvidenceReportError(contract.APS_RUNTIME_FAILURE_SOURCE_CITATION_PACK_INVALID, "section id mismatch", status_code=500)
        citations = [dict(item or {}) for item in list(section.get("citations") or []) if isinstance(item, dict)]
        if int(section.get("citation_count") or 0) != len(citations):
            raise EvidenceReportError(contract.APS_RUNTIME_FAILURE_SOURCE_CITATION_PACK_INVALID, "section citation count mismatch", status_code=500)
        ordinals = [int(item.get("citation_ordinal") or 0) for item in citations]
        if ordinals != sorted(ordinals):
            raise EvidenceReportError(contract.APS_RUNTIME_FAILURE_SOURCE_CITATION_PACK_INVALID, "section citation ordering mismatch", status_code=500)
        if ordinals:
            first_ordinals.append(ordinals[0])
        total_citations += len(citations)
    if int(payload.get("total_citations") or 0) != total_citations:
        raise EvidenceReportError(contract.APS_RUNTIME_FAILURE_SOURCE_CITATION_PACK_INVALID, "report citation count mismatch", status_code=500)
    if first_ordinals != sorted(first_ordinals):
        raise EvidenceReportError(contract.APS_RUNTIME_FAILURE_SOURCE_CITATION_PACK_INVALID, "section ordering mismatch", status_code=500)


def _validate_persisted_evidence_report_payload(payload: dict[str, Any]) -> dict[str, Any]:
    if str(payload.get("schema_id") or "") != contract.APS_EVIDENCE_REPORT_SCHEMA_ID:
        raise EvidenceReportError(contract.APS_RUNTIME_FAILURE_SOURCE_CITATION_PACK_INVALID, "evidence report schema mismatch", status_code=500)
    if int(payload.get("schema_version") or 0) != contract.APS_EVIDENCE_REPORT_SCHEMA_VERSION:
        raise EvidenceReportError(contract.APS_RUNTIME_FAILURE_SOURCE_CITATION_PACK_INVALID, "evidence report schema version mismatch", status_code=500)
    if str(payload.get("assembly_contract_id") or "") != contract.APS_EVIDENCE_REPORT_ASSEMBLY_CONTRACT_ID:
        raise EvidenceReportError(contract.APS_RUNTIME_FAILURE_SOURCE_CITATION_PACK_INVALID, "report assembly contract mismatch", status_code=500)
    if str(payload.get("sectioning_contract_id") or "") != contract.APS_EVIDENCE_REPORT_SECTIONING_CONTRACT_ID:
        raise EvidenceReportError(contract.APS_RUNTIME_FAILURE_SOURCE_CITATION_PACK_INVALID, "report sectioning contract mismatch", status_code=500)
    checksum = str(payload.get("evidence_report_checksum") or "").strip()
    expected_checksum = contract.compute_evidence_report_checksum(payload)
    if not checksum or checksum != expected_checksum:
        raise EvidenceReportError(contract.APS_RUNTIME_FAILURE_WRITE_FAILED, "evidence report checksum mismatch", status_code=500)
    _validate_section_rows(payload)
    return payload


def load_persisted_evidence_report_artifact(
    *,
    evidence_report_id: str | None = None,
    evidence_report_ref: str | Path | None = None,
) -> tuple[dict[str, Any], Path]:
    candidate_path = _resolve_evidence_report_artifact_path(evidence_report_id=evidence_report_id, evidence_report_ref=evidence_report_ref)
    payload = _read_json(candidate_path)
    if not payload:
        raise EvidenceReportError(contract.APS_RUNTIME_FAILURE_SOURCE_CITATION_PACK_INVALID, "evidence report artifact unreadable", status_code=500)
    validated_payload = _validate_persisted_evidence_report_payload(payload)
    validated_payload["_evidence_report_ref"] = str(candidate_path)
    validated_payload["_persisted"] = True
    return validated_payload, candidate_path


def _conflict_error(message: str, *, inner_code: str | None = None) -> EvidenceReportError:
    details = f"{message}: {inner_code}" if inner_code else message
    return EvidenceReportError(contract.APS_RUNTIME_FAILURE_CONFLICT, details, status_code=409)


def _persist_or_validate_evidence_report(*, artifact_path: Path, payload: dict[str, Any]) -> tuple[dict[str, Any], str]:
    if artifact_path.exists():
        try:
            existing_payload, existing_path = load_persisted_evidence_report_artifact(evidence_report_ref=artifact_path)
        except EvidenceReportError as exc:
            raise _conflict_error("existing persisted evidence report conflicts with derived report", inner_code=exc.code) from exc

        existing_report_id = str(existing_payload.get("evidence_report_id") or "").strip()
        expected_report_id = str(payload.get("evidence_report_id") or "").strip()
        if existing_report_id != expected_report_id:
            raise _conflict_error("existing persisted evidence report id conflicts with derived report")

        existing_checksum = str(existing_payload.get("evidence_report_checksum") or "").strip()
        expected_checksum = str(payload.get("evidence_report_checksum") or "").strip()
        if existing_checksum != expected_checksum:
            raise _conflict_error("existing persisted evidence report checksum conflicts with derived report")

        if contract.logical_evidence_report_payload(existing_payload) != contract.logical_evidence_report_payload(payload):
            raise _conflict_error("existing persisted evidence report body conflicts with derived report")
        return existing_payload, str(existing_path)

    evidence_report_ref = nrc_aps_safeguards.write_json_atomic(artifact_path, payload)
    validated_payload, _validated_path = load_persisted_evidence_report_artifact(evidence_report_ref=evidence_report_ref)
    return validated_payload, evidence_report_ref


def _append_evidence_report_summary(existing: list[dict[str, Any]] | None, entry: dict[str, Any]) -> list[dict[str, Any]]:
    summaries = [dict(item or {}) for item in (existing or []) if isinstance(item, dict)]
    incoming_report_id = str(entry.get("evidence_report_id") or "").strip()
    incoming_ref = str(entry.get("ref") or "").strip()
    kept: list[dict[str, Any]] = []
    replaced = False
    for item in summaries:
        same_report_id = str(item.get("evidence_report_id") or "").strip() == incoming_report_id
        same_ref = incoming_ref and str(item.get("ref") or "").strip() == incoming_ref
        if same_report_id or same_ref:
            if not replaced:
                kept.append(dict(entry))
                replaced = True
            continue
        kept.append(item)
    if not replaced:
        kept.append(dict(entry))
    kept.sort(key=lambda item: (str(item.get("evidence_report_id") or ""), str(item.get("ref") or "")))
    return kept


def _failure_source_locator(normalized_request: dict[str, Any], source_path: str | Path | None = None) -> str:
    return (
        str(normalized_request.get("citation_pack_id") or "").strip()
        or str(source_path or "").strip()
        or str(normalized_request.get("citation_pack_ref") or "").strip()
        or "unknown"
    )


def _persist_failure_artifact(
    db: Session,
    *,
    run: ConnectorRun | None,
    run_id: str | None,
    normalized_request: dict[str, Any],
    source_citation_pack_payload: dict[str, Any] | None,
    source_path: str | Path | None,
    error_code: str,
    error_message: str,
) -> str | None:
    if run is not None and not connector_run_is_baseline_visible(run):
        return None
    effective_run_id = str(run_id or getattr(run, "connector_run_id", "") or "").strip()
    if not effective_run_id:
        return None
    source_pack = dict(source_citation_pack_payload or {})
    failure_report_id = contract.derive_failure_report_id(
        source_locator=_failure_source_locator(normalized_request, source_path),
        error_code=error_code,
    )
    failure_payload = {
        "schema_id": contract.APS_EVIDENCE_REPORT_FAILURE_SCHEMA_ID,
        "schema_version": contract.APS_EVIDENCE_REPORT_SCHEMA_VERSION,
        "generated_at_utc": _utc_iso(),
        "evidence_report_id": failure_report_id,
        "run_id": effective_run_id,
        "assembly_contract_id": contract.APS_EVIDENCE_REPORT_ASSEMBLY_CONTRACT_ID,
        "sectioning_contract_id": contract.APS_EVIDENCE_REPORT_SECTIONING_CONTRACT_ID,
        "source_request": {
            "citation_pack_id": normalized_request.get("citation_pack_id"),
            "citation_pack_ref": normalized_request.get("citation_pack_ref"),
            "persist_report": bool(normalized_request.get("persist_report", False)),
        },
        "source_citation_pack": {
            "citation_pack_id": str(source_pack.get("citation_pack_id") or "").strip() or None,
            "citation_pack_checksum": str(source_pack.get("citation_pack_checksum") or "").strip() or None,
            "citation_pack_ref": str(source_path or source_pack.get("_citation_pack_ref") or source_pack.get("citation_pack_ref") or "").strip() or None,
        },
        "error_code": str(error_code or contract.APS_RUNTIME_FAILURE_INTERNAL),
        "error_message": str(error_message or ""),
    }
    failure_payload["evidence_report_checksum"] = contract.compute_evidence_report_checksum(failure_payload)
    failure_path = evidence_report_failure_artifact_path(
        run_id=effective_run_id,
        evidence_report_id=failure_report_id,
        reports_dir=settings.connector_reports_dir,
    )
    failure_ref = nrc_aps_safeguards.write_json_atomic(failure_path, failure_payload)
    if run is None:
        return failure_ref
    existing_refs = dict((run.query_plan_json or {}).get("aps_evidence_report_report_refs") or {})
    failure_refs = [str(item).strip() for item in list(existing_refs.get("aps_evidence_report_failures") or []) if str(item).strip()]
    if failure_ref not in failure_refs:
        failure_refs.append(failure_ref)
    run.query_plan_json = {
        **(run.query_plan_json or {}),
        "aps_evidence_report_report_refs": {
            "aps_evidence_reports": [str(item).strip() for item in list(existing_refs.get("aps_evidence_reports") or []) if str(item).strip()],
            "aps_evidence_report_failures": failure_refs,
        },
    }
    db.commit()
    return failure_ref


def _with_pagination(
    *,
    payload: dict[str, Any],
    limit: int,
    offset: int,
) -> dict[str, Any]:
    sections = [dict(item or {}) for item in list(payload.get("sections") or []) if isinstance(item, dict)]
    paged_sections = sections[offset : offset + limit]
    source_pack = dict(payload.get("source_citation_pack") or {})
    return {
        "schema_id": str(payload.get("schema_id") or contract.APS_EVIDENCE_REPORT_SCHEMA_ID),
        "schema_version": int(payload.get("schema_version") or contract.APS_EVIDENCE_REPORT_SCHEMA_VERSION),
        "evidence_report_id": str(payload.get("evidence_report_id") or ""),
        "evidence_report_checksum": str(payload.get("evidence_report_checksum") or ""),
        "evidence_report_ref": str(payload.get("_evidence_report_ref") or "") or None,
        "assembly_contract_id": str(payload.get("assembly_contract_id") or contract.APS_EVIDENCE_REPORT_ASSEMBLY_CONTRACT_ID),
        "sectioning_contract_id": str(payload.get("sectioning_contract_id") or contract.APS_EVIDENCE_REPORT_SECTIONING_CONTRACT_ID),
        "source_citation_pack": {
            **source_pack,
            "citation_pack_ref": str(source_pack.get("citation_pack_ref") or "") or None,
        },
        "total_sections": int(payload.get("total_sections") or 0),
        "total_citations": int(payload.get("total_citations") or 0),
        "total_groups": int(payload.get("total_groups") or 0),
        "limit": int(limit),
        "offset": int(offset),
        "persisted": bool(payload.get("_persisted", False)),
        "sections": paged_sections,
    }


def _candidate_run(db: Session, run_id: str | None) -> ConnectorRun | None:
    normalized_run_id = str(run_id or "").strip()
    if not normalized_run_id:
        return None
    return db.get(ConnectorRun, normalized_run_id)


def assemble_evidence_report(
    db: Session,
    *,
    request_payload: dict[str, Any],
) -> dict[str, Any]:
    try:
        normalized_request = contract.normalize_request_payload(request_payload)
    except ValueError as exc:
        code = str(exc) or contract.APS_RUNTIME_FAILURE_INVALID_REQUEST
        status_code = 422 if code in {"invalid_limit", "invalid_offset", contract.APS_RUNTIME_FAILURE_INVALID_REQUEST} else 400
        raise EvidenceReportError(code, f"invalid request: {code}", status_code=status_code) from None

    persist_report = bool(normalized_request.get("persist_report", False))
    source_path: Path | None = None
    raw_source_payload: dict[str, Any] = {}
    source_citation_pack_payload: dict[str, Any] | None = None
    run: ConnectorRun | None = None
    run_id: str | None = None
    try:
        source_path = nrc_aps_evidence_citation_pack.resolve_persisted_citation_pack_artifact_path(
            citation_pack_id=normalized_request.get("citation_pack_id"),
            citation_pack_ref=normalized_request.get("citation_pack_ref"),
        )
        raw_source_payload = nrc_aps_evidence_citation_pack.read_persisted_citation_pack_artifact_json(source_path)
        source_bundle = dict(raw_source_payload.get("source_bundle") or {})
        run_id = str(source_bundle.get("run_id") or "").strip() or None
        run = _candidate_run(db, run_id)
        source_citation_pack_payload, source_path = nrc_aps_evidence_citation_pack.load_persisted_citation_pack_artifact(citation_pack_ref=source_path)
        source_bundle = dict(source_citation_pack_payload.get("source_bundle") or {})
        run_id = str(source_bundle.get("run_id") or run_id or "").strip() or None
        if run is None:
            run = _candidate_run(db, run_id)
        source_citation_pack = contract.source_citation_pack_summary_payload(source_citation_pack_payload)
        evidence_report_id = contract.derive_evidence_report_id(
            citation_pack_id=str(source_citation_pack_payload.get("citation_pack_id") or ""),
            citation_pack_checksum=str(source_citation_pack_payload.get("citation_pack_checksum") or ""),
        )
        sections = contract.build_sections_from_citation_pack(source_citation_pack_payload)
        report_payload = {
            "schema_id": contract.APS_EVIDENCE_REPORT_SCHEMA_ID,
            "schema_version": contract.APS_EVIDENCE_REPORT_SCHEMA_VERSION,
            "generated_at_utc": _utc_iso(),
            "evidence_report_id": evidence_report_id,
            "assembly_contract_id": contract.APS_EVIDENCE_REPORT_ASSEMBLY_CONTRACT_ID,
            "sectioning_contract_id": contract.APS_EVIDENCE_REPORT_SECTIONING_CONTRACT_ID,
            "source_citation_pack": source_citation_pack,
            "total_sections": len(sections),
            "total_citations": int(source_citation_pack.get("total_citations") or 0),
            "total_groups": int(source_citation_pack.get("total_groups") or 0),
            "sections": sections,
        }
        report_payload["evidence_report_checksum"] = contract.compute_evidence_report_checksum(report_payload)

        if persist_report:
            if run is not None and not connector_run_is_baseline_visible(run):
                raise EvidenceReportError(
                    contract.APS_RUNTIME_FAILURE_INVALID_REQUEST,
                    "persist_report is unavailable for experiment-hidden runs",
                    status_code=422,
                )
            effective_run_id = str(run_id or "").strip()
            if not effective_run_id:
                raise EvidenceReportError(contract.APS_RUNTIME_FAILURE_SOURCE_CITATION_PACK_INVALID, "source citation pack missing run id", status_code=500)
            artifact_path = evidence_report_artifact_path(
                run_id=effective_run_id,
                evidence_report_id=evidence_report_id,
                reports_dir=settings.connector_reports_dir,
            )
            report_payload, evidence_report_ref = _persist_or_validate_evidence_report(artifact_path=artifact_path, payload=report_payload)
            if run is not None:
                existing_refs = dict((run.query_plan_json or {}).get("aps_evidence_report_report_refs") or {})
                report_refs = [str(item).strip() for item in list(existing_refs.get("aps_evidence_reports") or []) if str(item).strip()]
                if evidence_report_ref not in report_refs:
                    report_refs.append(evidence_report_ref)
                failure_refs = [str(item).strip() for item in list(existing_refs.get("aps_evidence_report_failures") or []) if str(item).strip()]
                summaries = _append_evidence_report_summary(
                    (run.query_plan_json or {}).get("aps_evidence_report_summaries"),
                    {
                        "evidence_report_id": evidence_report_id,
                        "source_citation_pack_id": str(source_citation_pack.get("citation_pack_id") or ""),
                        "source_citation_pack_checksum": str(source_citation_pack.get("citation_pack_checksum") or ""),
                        "total_sections": len(sections),
                        "total_citations": int(source_citation_pack.get("total_citations") or 0),
                        "total_groups": int(source_citation_pack.get("total_groups") or 0),
                        "ref": evidence_report_ref,
                    },
                )
                run.query_plan_json = {
                    **(run.query_plan_json or {}),
                    "aps_evidence_report_report_refs": {
                        "aps_evidence_reports": report_refs,
                        "aps_evidence_report_failures": failure_refs,
                    },
                    "aps_evidence_report_summaries": summaries,
                }
                db.commit()
            report_payload["_evidence_report_ref"] = evidence_report_ref
            report_payload["_persisted"] = True
        else:
            report_payload["_evidence_report_ref"] = None
            report_payload["_persisted"] = False

        return _with_pagination(
            payload=report_payload,
            limit=int(normalized_request.get("limit") or 0),
            offset=int(normalized_request.get("offset") or 0),
        )
    except nrc_aps_evidence_citation_pack.EvidenceCitationPackError as exc:
        error_code = (
            contract.APS_RUNTIME_FAILURE_SOURCE_CITATION_PACK_NOT_FOUND
            if int(exc.status_code) == 404
            else contract.APS_RUNTIME_FAILURE_SOURCE_CITATION_PACK_INVALID
        )
        wrapped = EvidenceReportError(error_code, str(exc.message), status_code=404 if error_code == contract.APS_RUNTIME_FAILURE_SOURCE_CITATION_PACK_NOT_FOUND else 422)
        if persist_report:
            _persist_failure_artifact(
                db,
                run=run,
                run_id=run_id,
                normalized_request=normalized_request,
                source_citation_pack_payload=raw_source_payload,
                source_path=source_path,
                error_code=wrapped.code,
                error_message=wrapped.message,
            )
        raise wrapped from None
    except EvidenceReportError as exc:
        if persist_report:
            _persist_failure_artifact(
                db,
                run=run,
                run_id=run_id,
                normalized_request=normalized_request,
                source_citation_pack_payload=source_citation_pack_payload or raw_source_payload,
                source_path=source_path,
                error_code=exc.code,
                error_message=exc.message,
            )
        raise
    except Exception as exc:  # noqa: BLE001
        if persist_report:
            _persist_failure_artifact(
                db,
                run=run,
                run_id=run_id,
                normalized_request=normalized_request,
                source_citation_pack_payload=source_citation_pack_payload or raw_source_payload,
                source_path=source_path,
                error_code=contract.APS_RUNTIME_FAILURE_INTERNAL,
                error_message=str(exc),
            )
        raise EvidenceReportError(contract.APS_RUNTIME_FAILURE_INTERNAL, str(exc), status_code=500) from exc


def get_persisted_evidence_report_page(
    *,
    evidence_report_id: str,
    limit: int | None = None,
    offset: int | None = None,
) -> dict[str, Any]:
    payload, _candidate_path = load_persisted_evidence_report_artifact(evidence_report_id=str(evidence_report_id or "").strip())
    try:
        resolved_limit, resolved_offset = contract.resolve_limit_offset(limit_value=limit, offset_value=offset)
    except ValueError as exc:
        code = str(exc) or contract.APS_RUNTIME_FAILURE_INVALID_REQUEST
        raise EvidenceReportError(code, f"invalid request: {code}", status_code=422) from None
    return _with_pagination(payload=payload, limit=resolved_limit, offset=resolved_offset)
