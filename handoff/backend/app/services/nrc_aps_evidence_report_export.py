from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from sqlalchemy.orm import Session

from app.core.config import settings
from app.models import ConnectorRun
from app.services import nrc_aps_evidence_report
from app.services import nrc_aps_evidence_report_export_contract as contract
from app.services import nrc_aps_safeguards


class EvidenceReportExportError(RuntimeError):
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


def evidence_report_export_artifact_path(*, run_id: str, evidence_report_export_id: str, reports_dir: str | Path) -> Path:
    scope = f"run_{_safe_scope_token(run_id)}"
    return Path(reports_dir) / contract.expected_export_file_name(scope=scope, evidence_report_export_id=evidence_report_export_id)


def evidence_report_export_failure_artifact_path(*, run_id: str, evidence_report_export_id: str, reports_dir: str | Path) -> Path:
    scope = f"run_{_safe_scope_token(run_id)}"
    return Path(reports_dir) / contract.expected_failure_file_name(scope=scope, evidence_report_export_id=evidence_report_export_id)


def find_evidence_report_export_artifact_by_id(*, evidence_report_export_id: str, reports_dir: str | Path) -> Path | None:
    pattern = f"*_{contract.artifact_id_token(evidence_report_export_id)}_aps_evidence_report_export_v1.json"
    candidates = sorted(Path(reports_dir).glob(pattern), key=lambda path: path.name)
    if not candidates:
        return None
    return candidates[0]


def _resolve_evidence_report_export_artifact_path(
    *,
    evidence_report_export_id: str | None = None,
    evidence_report_export_ref: str | Path | None = None,
) -> Path:
    normalized_export_id = str(evidence_report_export_id or "").strip()
    normalized_export_ref = str(evidence_report_export_ref or "").strip()
    if bool(normalized_export_id) == bool(normalized_export_ref):
        raise EvidenceReportExportError(
            contract.APS_RUNTIME_FAILURE_INVALID_REQUEST,
            "exactly one of evidence_report_export_id or evidence_report_export_ref is required",
            status_code=400,
        )
    if normalized_export_ref:
        candidate_path = Path(normalized_export_ref)
    else:
        candidate_path = find_evidence_report_export_artifact_by_id(
            evidence_report_export_id=normalized_export_id,
            reports_dir=settings.connector_reports_dir,
        )
        if candidate_path is None:
            raise EvidenceReportExportError(contract.APS_RUNTIME_FAILURE_EXPORT_NOT_FOUND, "evidence report export not found", status_code=404)
    if not candidate_path.exists():
        raise EvidenceReportExportError(contract.APS_RUNTIME_FAILURE_EXPORT_NOT_FOUND, "evidence report export not found", status_code=404)
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


def _validate_persisted_evidence_report_export_payload(payload: dict[str, Any]) -> dict[str, Any]:
    if str(payload.get("schema_id") or "") != contract.APS_EVIDENCE_REPORT_EXPORT_SCHEMA_ID:
        raise EvidenceReportExportError(contract.APS_RUNTIME_FAILURE_EXPORT_INVALID, "evidence report export schema mismatch", status_code=500)
    if int(payload.get("schema_version") or 0) != contract.APS_EVIDENCE_REPORT_EXPORT_SCHEMA_VERSION:
        raise EvidenceReportExportError(contract.APS_RUNTIME_FAILURE_EXPORT_INVALID, "evidence report export schema version mismatch", status_code=500)
    if str(payload.get("render_contract_id") or "") != contract.APS_EVIDENCE_REPORT_EXPORT_RENDER_CONTRACT_ID:
        raise EvidenceReportExportError(contract.APS_RUNTIME_FAILURE_EXPORT_INVALID, "render contract mismatch", status_code=500)
    if str(payload.get("template_contract_id") or "") != contract.APS_EVIDENCE_REPORT_EXPORT_MARKDOWN_TEMPLATE_CONTRACT_ID:
        raise EvidenceReportExportError(contract.APS_RUNTIME_FAILURE_EXPORT_INVALID, "template contract mismatch", status_code=500)
    if str(payload.get("format_id") or "") != contract.APS_EVIDENCE_REPORT_EXPORT_FORMAT_ID:
        raise EvidenceReportExportError(contract.APS_RUNTIME_FAILURE_EXPORT_INVALID, "format mismatch", status_code=500)
    if str(payload.get("media_type") or "") != contract.APS_EVIDENCE_REPORT_EXPORT_MEDIA_TYPE:
        raise EvidenceReportExportError(contract.APS_RUNTIME_FAILURE_EXPORT_INVALID, "media type mismatch", status_code=500)
    if str(payload.get("file_extension") or "") != contract.APS_EVIDENCE_REPORT_EXPORT_FILE_EXTENSION:
        raise EvidenceReportExportError(contract.APS_RUNTIME_FAILURE_EXPORT_INVALID, "file extension mismatch", status_code=500)

    rendered_markdown = str(payload.get("rendered_markdown") or "")
    rendered_markdown_sha256 = str(payload.get("rendered_markdown_sha256") or "").strip()
    expected_rendered_markdown_sha256 = contract.compute_rendered_markdown_sha256(rendered_markdown)
    if not rendered_markdown_sha256 or rendered_markdown_sha256 != expected_rendered_markdown_sha256:
        raise EvidenceReportExportError(contract.APS_RUNTIME_FAILURE_WRITE_FAILED, "rendered markdown hash mismatch", status_code=500)

    checksum = str(payload.get("evidence_report_export_checksum") or "").strip()
    expected_checksum = contract.compute_evidence_report_export_checksum(payload)
    if not checksum or checksum != expected_checksum:
        raise EvidenceReportExportError(contract.APS_RUNTIME_FAILURE_WRITE_FAILED, "evidence report export checksum mismatch", status_code=500)
    return payload


def load_persisted_evidence_report_export_artifact(
    *,
    evidence_report_export_id: str | None = None,
    evidence_report_export_ref: str | Path | None = None,
) -> tuple[dict[str, Any], Path]:
    candidate_path = _resolve_evidence_report_export_artifact_path(
        evidence_report_export_id=evidence_report_export_id,
        evidence_report_export_ref=evidence_report_export_ref,
    )
    payload = _read_json(candidate_path)
    if not payload:
        raise EvidenceReportExportError(contract.APS_RUNTIME_FAILURE_EXPORT_INVALID, "evidence report export artifact unreadable", status_code=500)
    validated_payload = _validate_persisted_evidence_report_export_payload(payload)
    validated_payload["_evidence_report_export_ref"] = str(candidate_path)
    validated_payload["_persisted"] = True
    return validated_payload, candidate_path


def _conflict_error(message: str, *, inner_code: str | None = None) -> EvidenceReportExportError:
    details = f"{message}: {inner_code}" if inner_code else message
    return EvidenceReportExportError(contract.APS_RUNTIME_FAILURE_CONFLICT, details, status_code=409)


def _persist_or_validate_evidence_report_export(*, artifact_path: Path, payload: dict[str, Any]) -> tuple[dict[str, Any], str]:
    if artifact_path.exists():
        try:
            existing_payload, existing_path = load_persisted_evidence_report_export_artifact(evidence_report_export_ref=artifact_path)
        except EvidenceReportExportError as exc:
            raise _conflict_error("existing persisted evidence report export conflicts with derived export", inner_code=exc.code) from exc

        existing_export_id = str(existing_payload.get("evidence_report_export_id") or "").strip()
        expected_export_id = str(payload.get("evidence_report_export_id") or "").strip()
        if existing_export_id != expected_export_id:
            raise _conflict_error("existing persisted evidence report export id conflicts with derived export")

        existing_checksum = str(existing_payload.get("evidence_report_export_checksum") or "").strip()
        expected_checksum = str(payload.get("evidence_report_export_checksum") or "").strip()
        if existing_checksum != expected_checksum:
            raise _conflict_error("existing persisted evidence report export checksum conflicts with derived export")

        if contract.logical_evidence_report_export_payload(existing_payload) != contract.logical_evidence_report_export_payload(payload):
            raise _conflict_error("existing persisted evidence report export body conflicts with derived export")
        return existing_payload, str(existing_path)

    evidence_report_export_ref = nrc_aps_safeguards.write_json_atomic(artifact_path, payload)
    validated_payload, _validated_path = load_persisted_evidence_report_export_artifact(
        evidence_report_export_ref=evidence_report_export_ref
    )
    return validated_payload, evidence_report_export_ref


def _append_evidence_report_export_summary(existing: list[dict[str, Any]] | None, entry: dict[str, Any]) -> list[dict[str, Any]]:
    summaries = [dict(item or {}) for item in (existing or []) if isinstance(item, dict)]
    incoming_export_id = str(entry.get("evidence_report_export_id") or "").strip()
    incoming_ref = str(entry.get("ref") or "").strip()
    kept: list[dict[str, Any]] = []
    replaced = False
    for item in summaries:
        same_export_id = str(item.get("evidence_report_export_id") or "").strip() == incoming_export_id
        same_ref = incoming_ref and str(item.get("ref") or "").strip() == incoming_ref
        if same_export_id or same_ref:
            if not replaced:
                kept.append(dict(entry))
                replaced = True
            continue
        kept.append(item)
    if not replaced:
        kept.append(dict(entry))
    kept.sort(key=lambda item: (str(item.get("evidence_report_export_id") or ""), str(item.get("ref") or "")))
    return kept


def _candidate_run(db: Session, run_id: str | None) -> ConnectorRun | None:
    normalized_run_id = str(run_id or "").strip()
    if not normalized_run_id:
        return None
    return db.get(ConnectorRun, normalized_run_id)


def _failure_source_locator(normalized_request: dict[str, Any], source_path: str | Path | None = None) -> str:
    return (
        str(normalized_request.get("evidence_report_id") or "").strip()
        or str(source_path or "").strip()
        or str(normalized_request.get("evidence_report_ref") or "").strip()
        or "unknown"
    )


def _persist_failure_artifact(
    db: Session,
    *,
    run: ConnectorRun | None,
    run_id: str | None,
    normalized_request: dict[str, Any],
    source_report_payload: dict[str, Any] | None,
    source_path: str | Path | None,
    error_code: str,
    error_message: str,
) -> str | None:
    effective_run_id = str(run_id or getattr(run, "connector_run_id", "") or "").strip()
    if not effective_run_id:
        return None
    source_report = dict(source_report_payload or {})
    failure_export_id = contract.derive_failure_export_id(
        source_locator=_failure_source_locator(normalized_request, source_path),
        error_code=error_code,
    )
    failure_payload = {
        "schema_id": contract.APS_EVIDENCE_REPORT_EXPORT_FAILURE_SCHEMA_ID,
        "schema_version": contract.APS_EVIDENCE_REPORT_EXPORT_SCHEMA_VERSION,
        "generated_at_utc": _utc_iso(),
        "evidence_report_export_id": failure_export_id,
        "run_id": effective_run_id,
        "render_contract_id": contract.APS_EVIDENCE_REPORT_EXPORT_RENDER_CONTRACT_ID,
        "template_contract_id": contract.APS_EVIDENCE_REPORT_EXPORT_MARKDOWN_TEMPLATE_CONTRACT_ID,
        "format_id": contract.APS_EVIDENCE_REPORT_EXPORT_FORMAT_ID,
        "source_request": {
            "evidence_report_id": normalized_request.get("evidence_report_id"),
            "evidence_report_ref": normalized_request.get("evidence_report_ref"),
            "persist_export": bool(normalized_request.get("persist_export", False)),
        },
        "source_evidence_report": {
            "evidence_report_id": str(source_report.get("evidence_report_id") or "").strip() or None,
            "evidence_report_checksum": str(source_report.get("evidence_report_checksum") or "").strip() or None,
            "evidence_report_ref": str(source_path or source_report.get("_evidence_report_ref") or source_report.get("evidence_report_ref") or "").strip() or None,
        },
        "error_code": str(error_code or contract.APS_RUNTIME_FAILURE_INTERNAL),
        "error_message": str(error_message or ""),
    }
    failure_payload["evidence_report_export_checksum"] = contract.compute_evidence_report_export_checksum(failure_payload)
    failure_path = evidence_report_export_failure_artifact_path(
        run_id=effective_run_id,
        evidence_report_export_id=failure_export_id,
        reports_dir=settings.connector_reports_dir,
    )
    failure_ref = nrc_aps_safeguards.write_json_atomic(failure_path, failure_payload)
    if run is None:
        return failure_ref
    existing_refs = dict((run.query_plan_json or {}).get("aps_evidence_report_export_report_refs") or {})
    failure_refs = [
        str(item).strip() for item in list(existing_refs.get("aps_evidence_report_export_failures") or []) if str(item).strip()
    ]
    if failure_ref not in failure_refs:
        failure_refs.append(failure_ref)
    run.query_plan_json = {
        **(run.query_plan_json or {}),
        "aps_evidence_report_export_report_refs": {
            "aps_evidence_report_exports": [
                str(item).strip() for item in list(existing_refs.get("aps_evidence_report_exports") or []) if str(item).strip()
            ],
            "aps_evidence_report_export_failures": failure_refs,
        },
    }
    db.commit()
    return failure_ref


def _response_payload(payload: dict[str, Any]) -> dict[str, Any]:
    return {
        "schema_id": str(payload.get("schema_id") or contract.APS_EVIDENCE_REPORT_EXPORT_SCHEMA_ID),
        "schema_version": int(payload.get("schema_version") or contract.APS_EVIDENCE_REPORT_EXPORT_SCHEMA_VERSION),
        "generated_at_utc": str(payload.get("generated_at_utc") or ""),
        "evidence_report_export_id": str(payload.get("evidence_report_export_id") or ""),
        "evidence_report_export_checksum": str(payload.get("evidence_report_export_checksum") or ""),
        "evidence_report_export_ref": str(payload.get("_evidence_report_export_ref") or "") or None,
        "render_contract_id": str(payload.get("render_contract_id") or contract.APS_EVIDENCE_REPORT_EXPORT_RENDER_CONTRACT_ID),
        "template_contract_id": str(
            payload.get("template_contract_id") or contract.APS_EVIDENCE_REPORT_EXPORT_MARKDOWN_TEMPLATE_CONTRACT_ID
        ),
        "format_id": str(payload.get("format_id") or contract.APS_EVIDENCE_REPORT_EXPORT_FORMAT_ID),
        "media_type": str(payload.get("media_type") or contract.APS_EVIDENCE_REPORT_EXPORT_MEDIA_TYPE),
        "file_extension": str(payload.get("file_extension") or contract.APS_EVIDENCE_REPORT_EXPORT_FILE_EXTENSION),
        "source_evidence_report": dict(payload.get("source_evidence_report") or {}),
        "total_sections": int(payload.get("total_sections") or 0),
        "total_citations": int(payload.get("total_citations") or 0),
        "total_groups": int(payload.get("total_groups") or 0),
        "rendered_markdown_sha256": str(payload.get("rendered_markdown_sha256") or ""),
        "rendered_markdown": str(payload.get("rendered_markdown") or ""),
        "persisted": bool(payload.get("_persisted", False)),
    }


def assemble_evidence_report_export(
    db: Session,
    *,
    request_payload: dict[str, Any],
) -> dict[str, Any]:
    try:
        normalized_request = contract.normalize_request_payload(request_payload)
    except ValueError as exc:
        code = str(exc) or contract.APS_RUNTIME_FAILURE_INVALID_REQUEST
        raise EvidenceReportExportError(code, f"invalid request: {code}", status_code=422) from None

    persist_export = bool(normalized_request.get("persist_export", False))
    source_path: Path | None = None
    raw_source_payload: dict[str, Any] = {}
    source_report_payload: dict[str, Any] | None = None
    run: ConnectorRun | None = None
    run_id: str | None = None
    try:
        source_path = nrc_aps_evidence_report.resolve_persisted_evidence_report_artifact_path(
            evidence_report_id=normalized_request.get("evidence_report_id"),
            evidence_report_ref=normalized_request.get("evidence_report_ref"),
        )
        raw_source_payload = nrc_aps_evidence_report.read_persisted_evidence_report_artifact_json(source_path)
        raw_source_citation_pack = dict(raw_source_payload.get("source_citation_pack") or {})
        raw_source_bundle = dict(raw_source_citation_pack.get("source_bundle") or {})
        run_id = str(raw_source_bundle.get("run_id") or "").strip() or None
        run = _candidate_run(db, run_id)
        source_report_payload, source_path = nrc_aps_evidence_report.load_persisted_evidence_report_artifact(
            evidence_report_ref=source_path,
        )
        source_citation_pack = dict(source_report_payload.get("source_citation_pack") or {})
        source_bundle = dict(source_citation_pack.get("source_bundle") or {})
        run_id = str(source_bundle.get("run_id") or "").strip() or None
        run = _candidate_run(db, run_id)

        export_payload = contract.build_evidence_report_export_payload(
            source_report_payload,
            generated_at_utc=_utc_iso(),
        )

        if persist_export:
            effective_run_id = str(run_id or "").strip()
            if not effective_run_id:
                raise EvidenceReportExportError(contract.APS_RUNTIME_FAILURE_SOURCE_REPORT_INVALID, "source evidence report missing run id", status_code=500)
            artifact_path = evidence_report_export_artifact_path(
                run_id=effective_run_id,
                evidence_report_export_id=str(export_payload.get("evidence_report_export_id") or ""),
                reports_dir=settings.connector_reports_dir,
            )
            export_payload, evidence_report_export_ref = _persist_or_validate_evidence_report_export(
                artifact_path=artifact_path,
                payload=export_payload,
            )
            if run is not None:
                existing_refs = dict((run.query_plan_json or {}).get("aps_evidence_report_export_report_refs") or {})
                export_refs = [
                    str(item).strip() for item in list(existing_refs.get("aps_evidence_report_exports") or []) if str(item).strip()
                ]
                if evidence_report_export_ref not in export_refs:
                    export_refs.append(evidence_report_export_ref)
                failure_refs = [
                    str(item).strip()
                    for item in list(existing_refs.get("aps_evidence_report_export_failures") or [])
                    if str(item).strip()
                ]
                summaries = _append_evidence_report_export_summary(
                    (run.query_plan_json or {}).get("aps_evidence_report_export_summaries"),
                    {
                        "evidence_report_export_id": str(export_payload.get("evidence_report_export_id") or ""),
                        "source_evidence_report_id": str(dict(export_payload.get("source_evidence_report") or {}).get("evidence_report_id") or ""),
                        "source_evidence_report_checksum": str(
                            dict(export_payload.get("source_evidence_report") or {}).get("evidence_report_checksum") or ""
                        ),
                        "format_id": str(export_payload.get("format_id") or ""),
                        "total_sections": int(export_payload.get("total_sections") or 0),
                        "total_citations": int(export_payload.get("total_citations") or 0),
                        "total_groups": int(export_payload.get("total_groups") or 0),
                        "ref": evidence_report_export_ref,
                    },
                )
                run.query_plan_json = {
                    **(run.query_plan_json or {}),
                    "aps_evidence_report_export_report_refs": {
                        "aps_evidence_report_exports": export_refs,
                        "aps_evidence_report_export_failures": failure_refs,
                    },
                    "aps_evidence_report_export_summaries": summaries,
                }
                db.commit()
            export_payload["_evidence_report_export_ref"] = evidence_report_export_ref
            export_payload["_persisted"] = True
        else:
            export_payload["_evidence_report_export_ref"] = None
            export_payload["_persisted"] = False

        return _response_payload(export_payload)
    except nrc_aps_evidence_report.EvidenceReportError as exc:
        error_code = (
            contract.APS_RUNTIME_FAILURE_SOURCE_REPORT_NOT_FOUND
            if int(exc.status_code) == 404
            else contract.APS_RUNTIME_FAILURE_SOURCE_REPORT_INVALID
        )
        wrapped = EvidenceReportExportError(
            error_code,
            str(exc.message),
            status_code=404 if error_code == contract.APS_RUNTIME_FAILURE_SOURCE_REPORT_NOT_FOUND else 422,
        )
        if persist_export:
            _persist_failure_artifact(
                db,
                run=run,
                run_id=run_id,
                normalized_request=normalized_request,
                source_report_payload=source_report_payload or raw_source_payload,
                source_path=source_path,
                error_code=wrapped.code,
                error_message=wrapped.message,
            )
        raise wrapped from None
    except EvidenceReportExportError as exc:
        if persist_export:
            _persist_failure_artifact(
                db,
                run=run,
                run_id=run_id,
                normalized_request=normalized_request,
                source_report_payload=source_report_payload,
                source_path=source_path,
                error_code=exc.code,
                error_message=exc.message,
            )
        raise
    except Exception as exc:  # noqa: BLE001
        if persist_export:
            _persist_failure_artifact(
                db,
                run=run,
                run_id=run_id,
                normalized_request=normalized_request,
                source_report_payload=source_report_payload,
                source_path=source_path,
                error_code=contract.APS_RUNTIME_FAILURE_INTERNAL,
                error_message=str(exc),
            )
        raise EvidenceReportExportError(contract.APS_RUNTIME_FAILURE_INTERNAL, str(exc), status_code=500) from exc


def get_persisted_evidence_report_export(
    *,
    evidence_report_export_id: str,
) -> dict[str, Any]:
    payload, _candidate_path = load_persisted_evidence_report_export_artifact(
        evidence_report_export_id=str(evidence_report_export_id or "").strip()
    )
    return _response_payload(payload)
