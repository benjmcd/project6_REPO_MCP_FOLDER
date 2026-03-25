from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from sqlalchemy.orm import Session

from app.core.config import settings
from app.models import ConnectorRun
from app.services import nrc_aps_evidence_bundle
from app.services import nrc_aps_evidence_bundle_contract as bundle_contract
from app.services import nrc_aps_evidence_citation_pack_contract as contract
from app.services import nrc_aps_safeguards


class EvidenceCitationPackError(RuntimeError):
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


def citation_pack_artifact_path(*, run_id: str, citation_pack_id: str, reports_dir: str | Path) -> Path:
    scope = f"run_{_safe_scope_token(run_id)}"
    return Path(reports_dir) / contract.expected_citation_pack_file_name(scope=scope, citation_pack_id=citation_pack_id)


def citation_pack_failure_artifact_path(*, run_id: str, citation_pack_id: str, reports_dir: str | Path) -> Path:
    scope = f"run_{_safe_scope_token(run_id)}"
    return Path(reports_dir) / contract.expected_failure_file_name(scope=scope, citation_pack_id=citation_pack_id)


def find_citation_pack_artifact_by_id(*, citation_pack_id: str, reports_dir: str | Path) -> Path | None:
    pattern = f"*_{contract.artifact_id_token(citation_pack_id)}_aps_evidence_citation_pack_v1.json"
    candidates = sorted(Path(reports_dir).glob(pattern), key=lambda path: path.name)
    if not candidates:
        return None
    return candidates[0]


def _resolve_citation_pack_artifact_path(
    *,
    citation_pack_id: str | None = None,
    citation_pack_ref: str | Path | None = None,
) -> Path:
    normalized_pack_id = str(citation_pack_id or "").strip()
    normalized_pack_ref = str(citation_pack_ref or "").strip()
    if bool(normalized_pack_id) == bool(normalized_pack_ref):
        raise EvidenceCitationPackError(contract.APS_RUNTIME_FAILURE_INVALID_REQUEST, "exactly one of citation_pack_id or citation_pack_ref is required", status_code=400)
    if normalized_pack_ref:
        candidate_path = Path(normalized_pack_ref)
    else:
        candidate_path = find_citation_pack_artifact_by_id(citation_pack_id=normalized_pack_id, reports_dir=settings.connector_reports_dir)
        if candidate_path is None:
            raise EvidenceCitationPackError(contract.APS_RUNTIME_FAILURE_SOURCE_BUNDLE_NOT_FOUND, "citation pack not found", status_code=404)
    if not candidate_path.exists():
        raise EvidenceCitationPackError(contract.APS_RUNTIME_FAILURE_SOURCE_BUNDLE_NOT_FOUND, "citation pack not found", status_code=404)
    return candidate_path


def resolve_persisted_citation_pack_artifact_path(
    *,
    citation_pack_id: str | None = None,
    citation_pack_ref: str | Path | None = None,
) -> Path:
    return _resolve_citation_pack_artifact_path(citation_pack_id=citation_pack_id, citation_pack_ref=citation_pack_ref)


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


def read_persisted_citation_pack_artifact_json(path: str | Path | None) -> dict[str, Any]:
    return _read_json(path)


def _validate_citation_rows(payload: dict[str, Any]) -> None:
    citations = [dict(item or {}) for item in (payload.get("citations") or []) if isinstance(item, dict)]
    expected_total_citations = len(citations)
    if int(payload.get("total_citations") or 0) != expected_total_citations:
        raise EvidenceCitationPackError(contract.APS_RUNTIME_FAILURE_SOURCE_BUNDLE_INVALID, "citation count mismatch", status_code=500)
    expected_total_groups = len({str(item.get("group_id") or "") for item in citations})
    if int(payload.get("total_groups") or 0) != expected_total_groups:
        raise EvidenceCitationPackError(contract.APS_RUNTIME_FAILURE_SOURCE_BUNDLE_INVALID, "group count mismatch", status_code=500)
    for index, citation in enumerate(citations, start=1):
        if int(citation.get("citation_ordinal") or 0) != index:
            raise EvidenceCitationPackError(contract.APS_RUNTIME_FAILURE_SOURCE_BUNDLE_INVALID, "citation ordinal mismatch", status_code=500)
        if str(citation.get("citation_label") or "") != contract.citation_label_for_ordinal(index):
            raise EvidenceCitationPackError(contract.APS_RUNTIME_FAILURE_SOURCE_BUNDLE_INVALID, "citation label mismatch", status_code=500)


def _validate_persisted_citation_pack_payload(payload: dict[str, Any]) -> dict[str, Any]:
    if str(payload.get("schema_id") or "") != contract.APS_EVIDENCE_CITATION_PACK_SCHEMA_ID:
        raise EvidenceCitationPackError(contract.APS_RUNTIME_FAILURE_SOURCE_BUNDLE_INVALID, "citation pack schema mismatch", status_code=500)
    if int(payload.get("schema_version") or 0) != contract.APS_EVIDENCE_CITATION_PACK_SCHEMA_VERSION:
        raise EvidenceCitationPackError(contract.APS_RUNTIME_FAILURE_SOURCE_BUNDLE_INVALID, "citation pack schema version mismatch", status_code=500)
    if str(payload.get("derivation_contract_id") or "") != contract.APS_EVIDENCE_CITATION_DERIVATION_CONTRACT_ID:
        raise EvidenceCitationPackError(contract.APS_RUNTIME_FAILURE_SOURCE_BUNDLE_INVALID, "citation derivation contract mismatch", status_code=500)
    checksum = str(payload.get("citation_pack_checksum") or "").strip()
    expected_checksum = contract.compute_citation_pack_checksum(payload)
    if not checksum or checksum != expected_checksum:
        raise EvidenceCitationPackError(contract.APS_RUNTIME_FAILURE_WRITE_FAILED, "citation pack checksum mismatch", status_code=500)
    _validate_citation_rows(payload)
    return payload


def load_persisted_citation_pack_artifact(
    *,
    citation_pack_id: str | None = None,
    citation_pack_ref: str | Path | None = None,
) -> tuple[dict[str, Any], Path]:
    candidate_path = _resolve_citation_pack_artifact_path(citation_pack_id=citation_pack_id, citation_pack_ref=citation_pack_ref)
    payload = _read_json(candidate_path)
    if not payload:
        raise EvidenceCitationPackError(contract.APS_RUNTIME_FAILURE_SOURCE_BUNDLE_INVALID, "citation pack artifact unreadable", status_code=500)
    validated_payload = _validate_persisted_citation_pack_payload(payload)
    validated_payload["_citation_pack_ref"] = str(candidate_path)
    validated_payload["_persisted"] = True
    return validated_payload, candidate_path


def _validate_source_bundle_for_citations(source_bundle_payload: dict[str, Any]) -> None:
    rows = [dict(item or {}) for item in (source_bundle_payload.get("results") or []) if isinstance(item, dict)]
    mode = str(source_bundle_payload.get("mode") or bundle_contract.APS_MODE_BROWSE)
    if not bundle_contract.is_ordering_deterministic(rows, mode=mode):
        raise EvidenceCitationPackError(contract.APS_RUNTIME_FAILURE_SOURCE_BUNDLE_INVALID, "source bundle ordering drift", status_code=500)
    for row in rows:
        if not bundle_contract.validate_known_contract_ids(row):
            raise EvidenceCitationPackError(
                contract.APS_RUNTIME_FAILURE_SOURCE_BUNDLE_UNKNOWN_CONTRACT,
                "unknown contract id in source bundle row",
                status_code=422,
            )
        missing = bundle_contract.missing_provenance_fields(row)
        if missing:
            raise EvidenceCitationPackError(
                contract.APS_RUNTIME_FAILURE_SOURCE_BUNDLE_PROVENANCE_MISSING,
                f"missing required provenance fields: {', '.join(sorted(missing))}",
                status_code=422,
            )
        unresolved = bundle_contract.unresolvable_provenance_fields(row)
        if unresolved:
            raise EvidenceCitationPackError(
                contract.APS_RUNTIME_FAILURE_SOURCE_BUNDLE_PROVENANCE_UNRESOLVABLE,
                f"unresolvable provenance fields: {', '.join(sorted(unresolved))}",
                status_code=422,
            )
        if not bundle_contract.validate_snippet_bounds(row):
            raise EvidenceCitationPackError(
                contract.APS_RUNTIME_FAILURE_SOURCE_BUNDLE_INVALID,
                f"invalid snippet bounds for chunk_id={row.get('chunk_id')}",
                status_code=500,
            )


def _persist_or_validate_citation_pack(*, artifact_path: Path, payload: dict[str, Any]) -> str:
    if artifact_path.exists():
        existing_payload = _read_json(artifact_path)
        existing_checksum = str(existing_payload.get("citation_pack_checksum") or "").strip()
        expected_checksum = str(payload.get("citation_pack_checksum") or "").strip()
        existing_pack_id = str(existing_payload.get("citation_pack_id") or "").strip()
        expected_pack_id = str(payload.get("citation_pack_id") or "").strip()
        if (
            existing_payload
            and existing_checksum
            and expected_checksum
            and existing_checksum == expected_checksum
            and existing_pack_id == expected_pack_id
        ):
            return str(artifact_path)
        if existing_payload and existing_pack_id and existing_pack_id == expected_pack_id:
            return str(artifact_path)
        raise EvidenceCitationPackError(
            contract.APS_RUNTIME_FAILURE_WRITE_FAILED,
            "existing persisted citation pack conflicts with immutable checksum",
            status_code=500,
        )
    return nrc_aps_safeguards.write_json_atomic(artifact_path, payload)


def _append_citation_pack_summary(existing: list[dict[str, Any]] | None, entry: dict[str, Any]) -> list[dict[str, Any]]:
    summaries = [dict(item or {}) for item in (existing or []) if isinstance(item, dict)]
    incoming_pack_id = str(entry.get("citation_pack_id") or "").strip()
    incoming_ref = str(entry.get("ref") or "").strip()
    kept: list[dict[str, Any]] = []
    replaced = False
    for item in summaries:
        same_pack_id = str(item.get("citation_pack_id") or "").strip() == incoming_pack_id
        same_ref = incoming_ref and str(item.get("ref") or "").strip() == incoming_ref
        if same_pack_id or same_ref:
            if not replaced:
                kept.append(dict(entry))
                replaced = True
            continue
        kept.append(item)
    if not replaced:
        kept.append(dict(entry))
    kept.sort(key=lambda item: (str(item.get("citation_pack_id") or ""), str(item.get("ref") or "")))
    return kept


def _failure_source_locator(normalized_request: dict[str, Any], source_path: str | Path | None = None) -> str:
    return (
        str(normalized_request.get("bundle_id") or "").strip()
        or str(source_path or "").strip()
        or str(normalized_request.get("bundle_ref") or "").strip()
        or "unknown"
    )


def _persist_failure_artifact(
    db: Session,
    *,
    run: ConnectorRun | None,
    run_id: str | None,
    normalized_request: dict[str, Any],
    source_bundle_payload: dict[str, Any] | None,
    source_path: str | Path | None,
    error_code: str,
    error_message: str,
) -> str | None:
    effective_run_id = str(run_id or getattr(run, "connector_run_id", "") or "").strip()
    if not effective_run_id:
        return None
    source_bundle = dict(source_bundle_payload or {})
    failure_pack_id = contract.derive_failure_pack_id(
        source_locator=_failure_source_locator(normalized_request, source_path),
        error_code=error_code,
    )
    failure_payload = {
        "schema_id": contract.APS_EVIDENCE_CITATION_PACK_FAILURE_SCHEMA_ID,
        "schema_version": contract.APS_EVIDENCE_CITATION_PACK_SCHEMA_VERSION,
        "generated_at_utc": _utc_iso(),
        "citation_pack_id": failure_pack_id,
        "run_id": effective_run_id,
        "derivation_contract_id": contract.APS_EVIDENCE_CITATION_DERIVATION_CONTRACT_ID,
        "source_request": {
            "bundle_id": normalized_request.get("bundle_id"),
            "bundle_ref": normalized_request.get("bundle_ref"),
            "persist_pack": bool(normalized_request.get("persist_pack", False)),
        },
        "source_bundle": {
            "bundle_id": str(source_bundle.get("bundle_id") or "").strip() or None,
            "bundle_checksum": str(source_bundle.get("bundle_checksum") or "").strip() or None,
            "bundle_ref": str(source_path or source_bundle.get("_bundle_ref") or source_bundle.get("bundle_ref") or "").strip() or None,
        },
        "error_code": str(error_code or contract.APS_RUNTIME_FAILURE_INTERNAL),
        "error_message": str(error_message or ""),
    }
    failure_payload["citation_pack_checksum"] = contract.compute_citation_pack_checksum(failure_payload)
    failure_path = citation_pack_failure_artifact_path(
        run_id=effective_run_id,
        citation_pack_id=failure_pack_id,
        reports_dir=settings.connector_reports_dir,
    )
    failure_ref = nrc_aps_safeguards.write_json_atomic(failure_path, failure_payload)
    if run is None:
        return failure_ref
    existing_refs = dict((run.query_plan_json or {}).get("aps_evidence_citation_pack_report_refs") or {})
    failure_refs = [str(item).strip() for item in list(existing_refs.get("aps_evidence_citation_pack_failures") or []) if str(item).strip()]
    if failure_ref not in failure_refs:
        failure_refs.append(failure_ref)
    run.query_plan_json = {
        **(run.query_plan_json or {}),
        "aps_evidence_citation_pack_report_refs": {
            "aps_evidence_citation_packs": [str(item).strip() for item in list(existing_refs.get("aps_evidence_citation_packs") or []) if str(item).strip()],
            "aps_evidence_citation_pack_failures": failure_refs,
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
    citations = [dict(item or {}) for item in (payload.get("citations") or []) if isinstance(item, dict)]
    paged_citations = citations[offset : offset + limit]
    source_bundle = dict(payload.get("source_bundle") or {})
    return {
        "schema_id": str(payload.get("schema_id") or contract.APS_EVIDENCE_CITATION_PACK_SCHEMA_ID),
        "schema_version": int(payload.get("schema_version") or contract.APS_EVIDENCE_CITATION_PACK_SCHEMA_VERSION),
        "citation_pack_id": str(payload.get("citation_pack_id") or ""),
        "citation_pack_checksum": str(payload.get("citation_pack_checksum") or ""),
        "citation_pack_ref": str(payload.get("_citation_pack_ref") or "") or None,
        "derivation_contract_id": str(payload.get("derivation_contract_id") or contract.APS_EVIDENCE_CITATION_DERIVATION_CONTRACT_ID),
        "source_bundle": {
            **source_bundle,
            "bundle_ref": str(source_bundle.get("bundle_ref") or "") or None,
        },
        "total_citations": int(payload.get("total_citations") or 0),
        "total_groups": int(payload.get("total_groups") or 0),
        "limit": int(limit),
        "offset": int(offset),
        "persisted": bool(payload.get("_persisted", False)),
        "citations": paged_citations,
    }


def _candidate_run(db: Session, run_id: str | None) -> ConnectorRun | None:
    normalized_run_id = str(run_id or "").strip()
    if not normalized_run_id:
        return None
    return db.get(ConnectorRun, normalized_run_id)


def assemble_evidence_citation_pack(
    db: Session,
    *,
    request_payload: dict[str, Any],
) -> dict[str, Any]:
    try:
        normalized_request = contract.normalize_request_payload(request_payload)
    except ValueError as exc:
        code = str(exc) or contract.APS_RUNTIME_FAILURE_INVALID_REQUEST
        status_code = 422 if code in {"invalid_limit", "invalid_offset", contract.APS_RUNTIME_FAILURE_INVALID_REQUEST} else 400
        raise EvidenceCitationPackError(code, f"invalid request: {code}", status_code=status_code) from None

    persist_pack = bool(normalized_request.get("persist_pack", False))
    source_path: Path | None = None
    raw_source_payload: dict[str, Any] = {}
    source_bundle_payload: dict[str, Any] | None = None
    run: ConnectorRun | None = None
    run_id: str | None = None
    try:
        source_path = nrc_aps_evidence_bundle.resolve_persisted_bundle_artifact_path(
            bundle_id=normalized_request.get("bundle_id"),
            bundle_ref=normalized_request.get("bundle_ref"),
        )
        raw_source_payload = nrc_aps_evidence_bundle.read_persisted_bundle_artifact_json(source_path)
        run_id = str(raw_source_payload.get("run_id") or "").strip() or None
        run = _candidate_run(db, run_id)
        source_bundle_payload, source_path = nrc_aps_evidence_bundle.load_persisted_bundle_artifact(bundle_ref=source_path)
        run_id = str(source_bundle_payload.get("run_id") or run_id or "").strip() or None
        if run is None:
            run = _candidate_run(db, run_id)
        _validate_source_bundle_for_citations(source_bundle_payload)
        source_bundle = contract.source_bundle_summary_payload(source_bundle_payload)
        citation_pack_id = contract.derive_citation_pack_id(
            source_bundle_id=str(source_bundle_payload.get("bundle_id") or ""),
            source_bundle_checksum=str(source_bundle_payload.get("bundle_checksum") or ""),
        )
        citations = contract.build_citations_from_bundle(source_bundle_payload)
        citation_pack_payload = {
            "schema_id": contract.APS_EVIDENCE_CITATION_PACK_SCHEMA_ID,
            "schema_version": contract.APS_EVIDENCE_CITATION_PACK_SCHEMA_VERSION,
            "generated_at_utc": _utc_iso(),
            "citation_pack_id": citation_pack_id,
            "derivation_contract_id": contract.APS_EVIDENCE_CITATION_DERIVATION_CONTRACT_ID,
            "source_bundle": source_bundle,
            "total_citations": len(citations),
            "total_groups": len({str(item.get("group_id") or "") for item in citations}),
            "citations": citations,
        }
        citation_pack_payload["citation_pack_checksum"] = contract.compute_citation_pack_checksum(citation_pack_payload)

        if persist_pack:
            effective_run_id = str(run_id or "").strip()
            if not effective_run_id:
                raise EvidenceCitationPackError(contract.APS_RUNTIME_FAILURE_SOURCE_BUNDLE_INVALID, "source bundle missing run id", status_code=500)
            artifact_path = citation_pack_artifact_path(
                run_id=effective_run_id,
                citation_pack_id=citation_pack_id,
                reports_dir=settings.connector_reports_dir,
            )
            citation_pack_ref = _persist_or_validate_citation_pack(artifact_path=artifact_path, payload=citation_pack_payload)
            persisted_payload = _read_json(citation_pack_ref)
            if persisted_payload:
                citation_pack_payload = persisted_payload
            if run is not None:
                existing_refs = dict((run.query_plan_json or {}).get("aps_evidence_citation_pack_report_refs") or {})
                pack_refs = [str(item).strip() for item in list(existing_refs.get("aps_evidence_citation_packs") or []) if str(item).strip()]
                if citation_pack_ref not in pack_refs:
                    pack_refs.append(citation_pack_ref)
                failure_refs = [str(item).strip() for item in list(existing_refs.get("aps_evidence_citation_pack_failures") or []) if str(item).strip()]
                summaries = _append_citation_pack_summary(
                    (run.query_plan_json or {}).get("aps_evidence_citation_pack_summaries"),
                    {
                        "citation_pack_id": citation_pack_id,
                        "source_bundle_id": str(source_bundle.get("bundle_id") or ""),
                        "source_bundle_checksum": str(source_bundle.get("bundle_checksum") or ""),
                        "total_citations": len(citations),
                        "total_groups": len({str(item.get("group_id") or "") for item in citations}),
                        "ref": citation_pack_ref,
                    },
                )
                run.query_plan_json = {
                    **(run.query_plan_json or {}),
                    "aps_evidence_citation_pack_report_refs": {
                        "aps_evidence_citation_packs": pack_refs,
                        "aps_evidence_citation_pack_failures": failure_refs,
                    },
                    "aps_evidence_citation_pack_summaries": summaries,
                }
                db.commit()
            citation_pack_payload["_citation_pack_ref"] = citation_pack_ref
            citation_pack_payload["_persisted"] = True
        else:
            citation_pack_payload["_citation_pack_ref"] = None
            citation_pack_payload["_persisted"] = False

        return _with_pagination(
            payload=citation_pack_payload,
            limit=int(normalized_request.get("limit") or 0),
            offset=int(normalized_request.get("offset") or 0),
        )
    except nrc_aps_evidence_bundle.EvidenceBundleError as exc:
        error_code = contract.APS_RUNTIME_FAILURE_SOURCE_BUNDLE_NOT_FOUND if int(exc.status_code) == 404 else contract.APS_RUNTIME_FAILURE_SOURCE_BUNDLE_INVALID
        wrapped = EvidenceCitationPackError(error_code, str(exc.message), status_code=404 if error_code == contract.APS_RUNTIME_FAILURE_SOURCE_BUNDLE_NOT_FOUND else 422)
        if persist_pack:
            _persist_failure_artifact(
                db,
                run=run,
                run_id=run_id,
                normalized_request=normalized_request,
                source_bundle_payload=raw_source_payload,
                source_path=source_path,
                error_code=wrapped.code,
                error_message=wrapped.message,
            )
        raise wrapped from None
    except EvidenceCitationPackError as exc:
        if persist_pack:
            _persist_failure_artifact(
                db,
                run=run,
                run_id=run_id,
                normalized_request=normalized_request,
                source_bundle_payload=source_bundle_payload or raw_source_payload,
                source_path=source_path,
                error_code=exc.code,
                error_message=exc.message,
            )
        raise
    except Exception as exc:  # noqa: BLE001
        if persist_pack:
            _persist_failure_artifact(
                db,
                run=run,
                run_id=run_id,
                normalized_request=normalized_request,
                source_bundle_payload=source_bundle_payload or raw_source_payload,
                source_path=source_path,
                error_code=contract.APS_RUNTIME_FAILURE_INTERNAL,
                error_message=str(exc),
            )
        raise EvidenceCitationPackError(contract.APS_RUNTIME_FAILURE_INTERNAL, str(exc), status_code=500) from exc


def get_persisted_citation_pack_page(
    *,
    citation_pack_id: str,
    limit: int | None = None,
    offset: int | None = None,
) -> dict[str, Any]:
    payload, _candidate_path = load_persisted_citation_pack_artifact(citation_pack_id=str(citation_pack_id or "").strip())
    try:
        resolved_limit, resolved_offset = contract.resolve_limit_offset(limit_value=limit, offset_value=offset)
    except ValueError as exc:
        code = str(exc) or contract.APS_RUNTIME_FAILURE_INVALID_REQUEST
        raise EvidenceCitationPackError(code, f"invalid request: {code}", status_code=422) from None
    return _with_pagination(payload=payload, limit=resolved_limit, offset=resolved_offset)
