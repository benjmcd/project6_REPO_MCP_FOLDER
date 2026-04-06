from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from sqlalchemy.orm import Session

from app.core.config import settings
from app.models import ConnectorRun
from app.services import nrc_aps_evidence_report_export
from app.services import nrc_aps_evidence_report_export_package_contract as contract
from app.services import nrc_aps_safeguards
from app.services.review_nrc_aps_runtime import connector_run_is_baseline_visible


class EvidenceReportExportPackageError(RuntimeError):
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


def evidence_report_export_package_artifact_path(
    *,
    owner_run_id: str,
    evidence_report_export_package_id: str,
    reports_dir: str | Path,
) -> Path:
    scope = f"run_{_safe_scope_token(owner_run_id)}"
    return Path(reports_dir) / contract.expected_package_file_name(
        scope=scope,
        evidence_report_export_package_id=evidence_report_export_package_id,
    )


def evidence_report_export_package_failure_artifact_path(
    *,
    owner_run_id: str,
    evidence_report_export_package_id: str,
    reports_dir: str | Path,
) -> Path:
    scope = f"run_{_safe_scope_token(owner_run_id)}"
    return Path(reports_dir) / contract.expected_failure_file_name(
        scope=scope,
        evidence_report_export_package_id=evidence_report_export_package_id,
    )


def find_evidence_report_export_package_artifact_by_id(
    *,
    evidence_report_export_package_id: str,
    reports_dir: str | Path,
) -> Path | None:
    pattern = (
        f"*_{contract.artifact_id_token(evidence_report_export_package_id)}"
        "_aps_evidence_report_export_package_v1.json"
    )
    candidates = sorted(Path(reports_dir).glob(pattern), key=lambda path: path.name)
    if not candidates:
        return None
    return candidates[0]


def _resolve_evidence_report_export_package_artifact_path(
    *,
    evidence_report_export_package_id: str | None = None,
    evidence_report_export_package_ref: str | Path | None = None,
) -> Path:
    normalized_package_id = str(evidence_report_export_package_id or "").strip()
    normalized_package_ref = str(evidence_report_export_package_ref or "").strip()
    if bool(normalized_package_id) == bool(normalized_package_ref):
        raise EvidenceReportExportPackageError(
            contract.APS_RUNTIME_FAILURE_INVALID_REQUEST,
            "exactly one of evidence_report_export_package_id or evidence_report_export_package_ref is required",
            status_code=400,
        )
    if normalized_package_ref:
        candidate_path = Path(normalized_package_ref)
    else:
        candidate_path = find_evidence_report_export_package_artifact_by_id(
            evidence_report_export_package_id=normalized_package_id,
            reports_dir=settings.connector_reports_dir,
        )
        if candidate_path is None:
            raise EvidenceReportExportPackageError(
                contract.APS_RUNTIME_FAILURE_PACKAGE_NOT_FOUND,
                "evidence report export package not found",
                status_code=404,
            )
    if not candidate_path.exists():
        raise EvidenceReportExportPackageError(
            contract.APS_RUNTIME_FAILURE_PACKAGE_NOT_FOUND,
            "evidence report export package not found",
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
    if str(payload.get("schema_id") or "") != contract.APS_EVIDENCE_REPORT_EXPORT_PACKAGE_FAILURE_SCHEMA_ID:
        raise EvidenceReportExportPackageError(
            contract.APS_RUNTIME_FAILURE_PACKAGE_INVALID,
            "evidence report export package failure schema mismatch",
            status_code=500,
        )
    if int(payload.get("schema_version") or 0) != contract.APS_EVIDENCE_REPORT_EXPORT_PACKAGE_SCHEMA_VERSION:
        raise EvidenceReportExportPackageError(
            contract.APS_RUNTIME_FAILURE_PACKAGE_INVALID,
            "evidence report export package failure schema version mismatch",
            status_code=500,
        )
    if str(payload.get("composition_contract_id") or "") != contract.APS_EVIDENCE_REPORT_EXPORT_PACKAGE_COMPOSITION_CONTRACT_ID:
        raise EvidenceReportExportPackageError(
            contract.APS_RUNTIME_FAILURE_PACKAGE_INVALID,
            "composition contract mismatch",
            status_code=500,
        )
    checksum = str(payload.get("evidence_report_export_package_checksum") or "").strip()
    expected_checksum = contract.compute_evidence_report_export_package_checksum(payload)
    if not checksum or checksum != expected_checksum:
        raise EvidenceReportExportPackageError(
            contract.APS_RUNTIME_FAILURE_PACKAGE_INVALID,
            "evidence report export package failure checksum mismatch",
            status_code=500,
        )
    return payload


def _validate_persisted_evidence_report_export_package_payload(payload: dict[str, Any]) -> dict[str, Any]:
    if str(payload.get("schema_id") or "") != contract.APS_EVIDENCE_REPORT_EXPORT_PACKAGE_SCHEMA_ID:
        raise EvidenceReportExportPackageError(
            contract.APS_RUNTIME_FAILURE_PACKAGE_INVALID,
            "evidence report export package schema mismatch",
            status_code=500,
        )
    if int(payload.get("schema_version") or 0) != contract.APS_EVIDENCE_REPORT_EXPORT_PACKAGE_SCHEMA_VERSION:
        raise EvidenceReportExportPackageError(
            contract.APS_RUNTIME_FAILURE_PACKAGE_INVALID,
            "evidence report export package schema version mismatch",
            status_code=500,
        )
    if str(payload.get("composition_contract_id") or "") != contract.APS_EVIDENCE_REPORT_EXPORT_PACKAGE_COMPOSITION_CONTRACT_ID:
        raise EvidenceReportExportPackageError(
            contract.APS_RUNTIME_FAILURE_PACKAGE_INVALID,
            "composition contract mismatch",
            status_code=500,
        )
    if str(payload.get("package_mode") or "") != contract.APS_EVIDENCE_REPORT_EXPORT_PACKAGE_MODE:
        raise EvidenceReportExportPackageError(
            contract.APS_RUNTIME_FAILURE_PACKAGE_INVALID,
            "package mode mismatch",
            status_code=500,
        )
    source_exports = [dict(item or {}) for item in list(payload.get("source_exports") or []) if isinstance(item, dict)]
    if int(payload.get("source_export_count") or 0) != len(source_exports):
        raise EvidenceReportExportPackageError(
            contract.APS_RUNTIME_FAILURE_PACKAGE_INVALID,
            "source export count mismatch",
            status_code=500,
        )
    if len(source_exports) < contract.APS_EVIDENCE_REPORT_EXPORT_PACKAGE_MIN_SOURCES:
        raise EvidenceReportExportPackageError(
            contract.APS_RUNTIME_FAILURE_PACKAGE_INVALID,
            "too few source exports",
            status_code=500,
        )
    seen_export_ids: set[str] = set()
    for index, source_export in enumerate(source_exports, start=1):
        if int(source_export.get("export_ordinal") or 0) != index:
            raise EvidenceReportExportPackageError(
                contract.APS_RUNTIME_FAILURE_PACKAGE_INVALID,
                "source export ordinal mismatch",
                status_code=500,
            )
        export_id = str(source_export.get("evidence_report_export_id") or "").strip()
        if not export_id:
            raise EvidenceReportExportPackageError(
                contract.APS_RUNTIME_FAILURE_PACKAGE_INVALID,
                "source export id missing",
                status_code=500,
            )
        if export_id in seen_export_ids:
            raise EvidenceReportExportPackageError(
                contract.APS_RUNTIME_FAILURE_PACKAGE_INVALID,
                "duplicate source export id",
                status_code=500,
            )
        seen_export_ids.add(export_id)
    ordered_digest = str(payload.get("ordered_source_exports_sha256") or "").strip()
    expected_ordered_digest = contract.ordered_source_exports_sha256(source_exports)
    if not ordered_digest or ordered_digest != expected_ordered_digest:
        raise EvidenceReportExportPackageError(
            contract.APS_RUNTIME_FAILURE_PACKAGE_INVALID,
            "ordered source exports digest mismatch",
            status_code=500,
        )
    checksum = str(payload.get("evidence_report_export_package_checksum") or "").strip()
    expected_checksum = contract.compute_evidence_report_export_package_checksum(payload)
    if not checksum or checksum != expected_checksum:
        raise EvidenceReportExportPackageError(
            contract.APS_RUNTIME_FAILURE_PACKAGE_INVALID,
            "evidence report export package checksum mismatch",
            status_code=500,
        )
    return payload


def load_persisted_evidence_report_export_package_artifact(
    *,
    evidence_report_export_package_id: str | None = None,
    evidence_report_export_package_ref: str | Path | None = None,
) -> tuple[dict[str, Any], Path]:
    candidate_path = _resolve_evidence_report_export_package_artifact_path(
        evidence_report_export_package_id=evidence_report_export_package_id,
        evidence_report_export_package_ref=evidence_report_export_package_ref,
    )
    payload = _read_json(candidate_path)
    if not payload:
        raise EvidenceReportExportPackageError(
            contract.APS_RUNTIME_FAILURE_PACKAGE_INVALID,
            "evidence report export package artifact unreadable",
            status_code=500,
        )
    validated_payload = _validate_persisted_evidence_report_export_package_payload(payload)
    validated_payload["_evidence_report_export_package_ref"] = str(candidate_path)
    validated_payload["_persisted"] = True
    return validated_payload, candidate_path


def _conflict_error(message: str, *, inner_code: str | None = None) -> EvidenceReportExportPackageError:
    details = f"{message}: {inner_code}" if inner_code else message
    return EvidenceReportExportPackageError(contract.APS_RUNTIME_FAILURE_CONFLICT, details, status_code=409)


def _persist_or_validate_evidence_report_export_package(
    *,
    artifact_path: Path,
    payload: dict[str, Any],
) -> tuple[dict[str, Any], str]:
    if artifact_path.exists():
        try:
            existing_payload, existing_path = load_persisted_evidence_report_export_package_artifact(
                evidence_report_export_package_ref=artifact_path
            )
        except EvidenceReportExportPackageError as exc:
            raise _conflict_error(
                "existing persisted evidence report export package conflicts with derived package",
                inner_code=exc.code,
            ) from exc
        existing_package_id = str(existing_payload.get("evidence_report_export_package_id") or "").strip()
        expected_package_id = str(payload.get("evidence_report_export_package_id") or "").strip()
        if existing_package_id != expected_package_id:
            raise _conflict_error("existing persisted evidence report export package id conflicts with derived package")
        existing_checksum = str(existing_payload.get("evidence_report_export_package_checksum") or "").strip()
        expected_checksum = str(payload.get("evidence_report_export_package_checksum") or "").strip()
        if existing_checksum != expected_checksum:
            raise _conflict_error(
                "existing persisted evidence report export package checksum conflicts with derived package"
            )
        if contract.logical_evidence_report_export_package_payload(existing_payload) != contract.logical_evidence_report_export_package_payload(payload):
            raise _conflict_error("existing persisted evidence report export package body conflicts with derived package")
        return existing_payload, str(existing_path)

    evidence_report_export_package_ref = nrc_aps_safeguards.write_json_atomic(artifact_path, payload)
    validated_payload, _validated_path = load_persisted_evidence_report_export_package_artifact(
        evidence_report_export_package_ref=evidence_report_export_package_ref
    )
    return validated_payload, evidence_report_export_package_ref


def _append_evidence_report_export_package_summary(
    existing: list[dict[str, Any]] | None,
    entry: dict[str, Any],
) -> list[dict[str, Any]]:
    summaries = [dict(item or {}) for item in (existing or []) if isinstance(item, dict)]
    incoming_package_id = str(entry.get("evidence_report_export_package_id") or "").strip()
    incoming_ref = str(entry.get("ref") or "").strip()
    kept: list[dict[str, Any]] = []
    replaced = False
    for item in summaries:
        same_package_id = str(item.get("evidence_report_export_package_id") or "").strip() == incoming_package_id
        same_ref = incoming_ref and str(item.get("ref") or "").strip() == incoming_ref
        if same_package_id or same_ref:
            if not replaced:
                kept.append(dict(entry))
                replaced = True
            continue
        kept.append(item)
    if not replaced:
        kept.append(dict(entry))
    kept.sort(
        key=lambda item: (
            str(item.get("evidence_report_export_package_id") or ""),
            str(item.get("ref") or ""),
        )
    )
    return kept


def _candidate_run(db: Session, run_id: str | None) -> ConnectorRun | None:
    normalized_run_id = str(run_id or "").strip()
    if not normalized_run_id:
        return None
    return db.get(ConnectorRun, normalized_run_id)


def _response_payload(payload: dict[str, Any]) -> dict[str, Any]:
    return {
        "schema_id": str(payload.get("schema_id") or contract.APS_EVIDENCE_REPORT_EXPORT_PACKAGE_SCHEMA_ID),
        "schema_version": int(payload.get("schema_version") or contract.APS_EVIDENCE_REPORT_EXPORT_PACKAGE_SCHEMA_VERSION),
        "generated_at_utc": str(payload.get("generated_at_utc") or ""),
        "evidence_report_export_package_id": str(payload.get("evidence_report_export_package_id") or ""),
        "evidence_report_export_package_checksum": str(payload.get("evidence_report_export_package_checksum") or ""),
        "evidence_report_export_package_ref": str(payload.get("_evidence_report_export_package_ref") or "") or None,
        "composition_contract_id": str(
            payload.get("composition_contract_id") or contract.APS_EVIDENCE_REPORT_EXPORT_PACKAGE_COMPOSITION_CONTRACT_ID
        ),
        "package_mode": str(payload.get("package_mode") or contract.APS_EVIDENCE_REPORT_EXPORT_PACKAGE_MODE),
        "owner_run_id": str(payload.get("owner_run_id") or ""),
        "format_id": str(payload.get("format_id") or ""),
        "media_type": str(payload.get("media_type") or ""),
        "file_extension": str(payload.get("file_extension") or ""),
        "render_contract_id": str(payload.get("render_contract_id") or ""),
        "template_contract_id": str(payload.get("template_contract_id") or ""),
        "source_export_count": int(payload.get("source_export_count") or 0),
        "total_sections": int(payload.get("total_sections") or 0),
        "total_citations": int(payload.get("total_citations") or 0),
        "total_groups": int(payload.get("total_groups") or 0),
        "ordered_source_exports_sha256": str(payload.get("ordered_source_exports_sha256") or ""),
        "persisted": bool(payload.get("_persisted", False)),
        "source_exports": [dict(item or {}) for item in list(payload.get("source_exports") or []) if isinstance(item, dict)],
    }


def _resolve_export_payloads(
    normalized_request: dict[str, Any],
) -> tuple[list[dict[str, Any]], list[str], list[Path]]:
    source_ids = list(normalized_request.get("evidence_report_export_ids") or [])
    source_refs = list(normalized_request.get("evidence_report_export_refs") or [])
    source_paths: list[Path] = []
    source_payloads: list[dict[str, Any]] = []
    owner_run_ids: list[str] = []
    if source_ids:
        raw_values = source_ids
        key_name = "evidence_report_export_id"
    else:
        raw_values = source_refs
        key_name = "evidence_report_export_ref"
    for raw_value in raw_values:
        try:
            payload, source_path = nrc_aps_evidence_report_export.load_persisted_evidence_report_export_artifact(
                **{key_name: raw_value}
            )
        except nrc_aps_evidence_report_export.EvidenceReportExportError as exc:
            error_code = (
                contract.APS_RUNTIME_FAILURE_SOURCE_EXPORT_NOT_FOUND
                if int(exc.status_code) == 404
                else contract.APS_RUNTIME_FAILURE_SOURCE_EXPORT_INVALID
            )
            status_code = 404 if error_code == contract.APS_RUNTIME_FAILURE_SOURCE_EXPORT_NOT_FOUND else 422
            raise EvidenceReportExportPackageError(error_code, str(exc.message), status_code=status_code) from exc
        source_paths.append(source_path)
        source_payloads.append(payload)
        owner_run_id = contract.owner_run_id_for_export_payload(payload)
        if not owner_run_id:
            raise EvidenceReportExportPackageError(
                contract.APS_RUNTIME_FAILURE_SOURCE_EXPORT_INVALID,
                "source export missing owner run id",
                status_code=422,
            )
        owner_run_ids.append(owner_run_id)
    return source_payloads, owner_run_ids, source_paths


def _failure_source_locator(normalized_request: dict[str, Any]) -> str:
    source_ids = [str(item).strip() for item in list(normalized_request.get("evidence_report_export_ids") or []) if str(item).strip()]
    source_refs = [str(item).strip() for item in list(normalized_request.get("evidence_report_export_refs") or []) if str(item).strip()]
    source_locator = source_ids or source_refs
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
) -> str | None:
    if run is not None and not connector_run_is_baseline_visible(run):
        return None
    effective_run_id = str(owner_run_id or getattr(run, "connector_run_id", "") or "").strip()
    if not effective_run_id:
        return None
    failure_package_id = contract.derive_failure_package_id(
        source_locator=_failure_source_locator(normalized_request),
        error_code=error_code,
    )
    failure_payload = {
        "schema_id": contract.APS_EVIDENCE_REPORT_EXPORT_PACKAGE_FAILURE_SCHEMA_ID,
        "schema_version": contract.APS_EVIDENCE_REPORT_EXPORT_PACKAGE_SCHEMA_VERSION,
        "generated_at_utc": _utc_iso(),
        "evidence_report_export_package_id": failure_package_id,
        "owner_run_id": effective_run_id,
        "composition_contract_id": contract.APS_EVIDENCE_REPORT_EXPORT_PACKAGE_COMPOSITION_CONTRACT_ID,
        "package_mode": contract.APS_EVIDENCE_REPORT_EXPORT_PACKAGE_MODE,
        "source_request": {
            "evidence_report_export_ids": list(normalized_request.get("evidence_report_export_ids") or []),
            "evidence_report_export_refs": list(normalized_request.get("evidence_report_export_refs") or []),
            "persist_package": bool(normalized_request.get("persist_package", False)),
        },
        "source_exports": [
            {
                "evidence_report_export_id": str(payload.get("evidence_report_export_id") or "").strip() or None,
                "evidence_report_export_checksum": str(payload.get("evidence_report_export_checksum") or "").strip() or None,
                "evidence_report_export_ref": str(
                    payload.get("_evidence_report_export_ref") or payload.get("evidence_report_export_ref") or ""
                ).strip()
                or None,
            }
            for payload in list(source_payloads or [])
            if isinstance(payload, dict)
        ],
        "error_code": str(error_code or contract.APS_RUNTIME_FAILURE_INTERNAL),
        "error_message": str(error_message or ""),
    }
    failure_payload["evidence_report_export_package_checksum"] = contract.compute_evidence_report_export_package_checksum(
        failure_payload
    )
    failure_path = evidence_report_export_package_failure_artifact_path(
        owner_run_id=effective_run_id,
        evidence_report_export_package_id=failure_package_id,
        reports_dir=settings.connector_reports_dir,
    )
    failure_ref = nrc_aps_safeguards.write_json_atomic(failure_path, failure_payload)
    if run is None:
        return failure_ref
    existing_refs = dict((run.query_plan_json or {}).get("aps_evidence_report_export_package_report_refs") or {})
    failure_refs = [
        str(item).strip()
        for item in list(existing_refs.get("aps_evidence_report_export_package_failures") or [])
        if str(item).strip()
    ]
    if failure_ref not in failure_refs:
        failure_refs.append(failure_ref)
    run.query_plan_json = {
        **(run.query_plan_json or {}),
        "aps_evidence_report_export_package_report_refs": {
            "aps_evidence_report_export_packages": [
                str(item).strip()
                for item in list(existing_refs.get("aps_evidence_report_export_packages") or [])
                if str(item).strip()
            ],
            "aps_evidence_report_export_package_failures": failure_refs,
        },
    }
    db.commit()
    return failure_ref


def assemble_evidence_report_export_package(
    db: Session,
    *,
    request_payload: dict[str, Any],
) -> dict[str, Any]:
    try:
        normalized_request = contract.normalize_request_payload(request_payload)
    except ValueError as exc:
        code = str(exc) or contract.APS_RUNTIME_FAILURE_INVALID_REQUEST
        raise EvidenceReportExportPackageError(code, f"invalid request: {code}", status_code=422) from None

    persist_package = bool(normalized_request.get("persist_package", False))
    source_payloads: list[dict[str, Any]] = []
    owner_run_ids: list[str] = []
    run: ConnectorRun | None = None
    owner_run_id: str | None = None
    try:
        source_payloads, owner_run_ids, _source_paths = _resolve_export_payloads(normalized_request)
        unique_owner_run_ids = sorted(set(owner_run_ids))
        if len(unique_owner_run_ids) > 1:
            raise EvidenceReportExportPackageError(
                contract.APS_RUNTIME_FAILURE_CROSS_RUN_UNSUPPORTED,
                "cross-run package composition is not supported in v1",
                status_code=409,
            )
        owner_run_id = unique_owner_run_ids[0]
        run = _candidate_run(db, owner_run_id)

        try:
            package_payload = contract.build_evidence_report_export_package_payload(
                source_payloads,
                generated_at_utc=_utc_iso(),
                owner_run_id=owner_run_id,
            )
        except ValueError as exc:
            code = str(exc) or contract.APS_RUNTIME_FAILURE_SOURCE_EXPORT_INCOMPATIBLE
            raise EvidenceReportExportPackageError(code, f"source export incompatible: {code}", status_code=409) from None

        if persist_package:
            if run is not None and not connector_run_is_baseline_visible(run):
                raise EvidenceReportExportPackageError(
                    contract.APS_RUNTIME_FAILURE_INVALID_REQUEST,
                    "persist_package is unavailable for experiment-hidden runs",
                    status_code=422,
                )
            artifact_path = evidence_report_export_package_artifact_path(
                owner_run_id=owner_run_id,
                evidence_report_export_package_id=str(package_payload.get("evidence_report_export_package_id") or ""),
                reports_dir=settings.connector_reports_dir,
            )
            package_payload, package_ref = _persist_or_validate_evidence_report_export_package(
                artifact_path=artifact_path,
                payload=package_payload,
            )
            if run is not None:
                existing_refs = dict((run.query_plan_json or {}).get("aps_evidence_report_export_package_report_refs") or {})
                package_refs = [
                    str(item).strip()
                    for item in list(existing_refs.get("aps_evidence_report_export_packages") or [])
                    if str(item).strip()
                ]
                if package_ref not in package_refs:
                    package_refs.append(package_ref)
                failure_refs = [
                    str(item).strip()
                    for item in list(existing_refs.get("aps_evidence_report_export_package_failures") or [])
                    if str(item).strip()
                ]
                summaries = _append_evidence_report_export_package_summary(
                    (run.query_plan_json or {}).get("aps_evidence_report_export_package_summaries"),
                    {
                        "evidence_report_export_package_id": str(
                            package_payload.get("evidence_report_export_package_id") or ""
                        ),
                        "evidence_report_export_package_checksum": str(
                            package_payload.get("evidence_report_export_package_checksum") or ""
                        ),
                        "package_mode": str(package_payload.get("package_mode") or ""),
                        "owner_run_id": str(package_payload.get("owner_run_id") or ""),
                        "format_id": str(package_payload.get("format_id") or ""),
                        "source_export_count": int(package_payload.get("source_export_count") or 0),
                        "total_sections": int(package_payload.get("total_sections") or 0),
                        "total_citations": int(package_payload.get("total_citations") or 0),
                        "total_groups": int(package_payload.get("total_groups") or 0),
                        "ordered_source_exports_sha256": str(
                            package_payload.get("ordered_source_exports_sha256") or ""
                        ),
                        "ref": package_ref,
                    },
                )
                run.query_plan_json = {
                    **(run.query_plan_json or {}),
                    "aps_evidence_report_export_package_report_refs": {
                        "aps_evidence_report_export_packages": package_refs,
                        "aps_evidence_report_export_package_failures": failure_refs,
                    },
                    "aps_evidence_report_export_package_summaries": summaries,
                }
                db.commit()
            package_payload["_evidence_report_export_package_ref"] = package_ref
            package_payload["_persisted"] = True
        else:
            package_payload["_evidence_report_export_package_ref"] = None
            package_payload["_persisted"] = False
        return _response_payload(package_payload)
    except EvidenceReportExportPackageError as exc:
        if persist_package:
            _persist_failure_artifact(
                db,
                run=run,
                owner_run_id=owner_run_id,
                normalized_request=normalized_request,
                source_payloads=source_payloads,
                error_code=exc.code,
                error_message=exc.message,
            )
        raise
    except Exception as exc:  # noqa: BLE001
        if persist_package:
            _persist_failure_artifact(
                db,
                run=run,
                owner_run_id=owner_run_id,
                normalized_request=normalized_request,
                source_payloads=source_payloads,
                error_code=contract.APS_RUNTIME_FAILURE_INTERNAL,
                error_message=str(exc),
            )
        raise EvidenceReportExportPackageError(contract.APS_RUNTIME_FAILURE_INTERNAL, str(exc), status_code=500) from exc


def get_persisted_evidence_report_export_package(
    *,
    evidence_report_export_package_id: str,
) -> dict[str, Any]:
    payload, _candidate_path = load_persisted_evidence_report_export_package_artifact(
        evidence_report_export_package_id=str(evidence_report_export_package_id or "").strip()
    )
    return _response_payload(payload)
