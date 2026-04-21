from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.models import L3OutputPackage, L3ReconciliationRecord, L3Session, uuid_str
from app.services import nrc_aps_evidence_report as aps_report
from app.services import nrc_aps_evidence_report_export as aps_report_export
from app.services import nrc_aps_evidence_report_export_package as aps_export_package
from app.services import nrc_aps_evidence_report_export_package_contract as aps_export_package_contract
from app.services.layer3_aps_multisource import (
    APS_MULTISOURCE_GROUPING_CONTRACT_ID,
    APS_MULTISOURCE_SCHEMA_ID,
    PACKAGE_KIND_APS_MULTISOURCE_ADMISSION,
)
from app.services.layer3_package_entry import (
    PACKAGE_STATUS_COMPLETE,
    PACKAGE_STATUS_COMPLETE_WITH_WARNINGS,
)
from app.services.layer3_session_entry import (
    SESSION_STATUS_COMPLETED,
    SESSION_STATUS_COMPLETED_WITH_WARNINGS,
    SESSION_STATUS_FAILED,
)


PACKAGE_KIND_APS_EVIDENCE_REPORT_EXPORT_PACKAGE_HANDOFF = "aps_evidence_report_export_package_handoff"
APS_REPORT_EXPORT_PACKAGE_HANDOFF_SCHEMA_ID = "layer3.aps_evidence_report_export_package_handoff.v1"
APS_REPORT_EXPORT_PACKAGE_HANDOFF_SCHEMA_VERSION = 1
SOURCE_GATE_D_APS_EXPORT_PACKAGE_FREEZE = "15_GATED_APS_EXPORT_PACKAGE_FREEZE"

TERMINAL_SESSION_STATUSES = frozenset(
    {
        SESSION_STATUS_COMPLETED,
        SESSION_STATUS_COMPLETED_WITH_WARNINGS,
        SESSION_STATUS_FAILED,
    }
)
ACCEPTED_SOURCE_PACKAGE_STATUSES = frozenset(
    {
        PACKAGE_STATUS_COMPLETE,
        PACKAGE_STATUS_COMPLETE_WITH_WARNINGS,
    }
)


class Layer3ApsReportExportPackageHandoffError(ValueError):
    pass


@dataclass(frozen=True)
class Layer3ApsReportExportPackageHandoffResult:
    output_package: L3OutputPackage
    evidence_report_export_package_payload: dict[str, Any]


def _utc_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _require_existing_ref(ref: str | None, *, label: str) -> str:
    normalized = str(ref or "").strip()
    if not normalized:
        raise Layer3ApsReportExportPackageHandoffError(f"{label} is missing")
    if not Path(normalized).exists():
        raise Layer3ApsReportExportPackageHandoffError(f"{label} does not exist: {normalized}")
    return normalized


def _load_session_or_raise(db: Session, *, session_id: str) -> L3Session:
    session = db.get(L3Session, session_id)
    if session is None:
        raise Layer3ApsReportExportPackageHandoffError(f"Layer 3 session '{session_id}' was not found")
    if session.status not in TERMINAL_SESSION_STATUSES or session.completed_at is None:
        raise Layer3ApsReportExportPackageHandoffError(
            f"Layer 3 session '{session_id}' must be terminal before Gate D APS export-package handoff"
        )
    return session


def _load_source_package_or_raise(
    db: Session,
    *,
    session_id: str,
) -> tuple[L3OutputPackage, L3ReconciliationRecord, dict[str, Any], dict[str, Any]]:
    rows = (
        db.query(L3OutputPackage)
        .filter(L3OutputPackage.session_id == session_id)
        .order_by(L3OutputPackage.package_kind.asc())
        .all()
    )
    rows_by_kind = {row.package_kind: row for row in rows}
    if PACKAGE_KIND_APS_EVIDENCE_REPORT_EXPORT_PACKAGE_HANDOFF in rows_by_kind:
        raise Layer3ApsReportExportPackageHandoffError(
            f"Layer 3 session '{session_id}' already has an APS export-package handoff package"
        )
    source_row = rows_by_kind.get(PACKAGE_KIND_APS_MULTISOURCE_ADMISSION)
    if source_row is None:
        raise Layer3ApsReportExportPackageHandoffError(
            f"Layer 3 session '{session_id}' is missing the APS multisource admission package required for APS export-package handoff"
        )
    if source_row.status not in ACCEPTED_SOURCE_PACKAGE_STATUSES:
        raise Layer3ApsReportExportPackageHandoffError(
            f"Layer 3 package '{PACKAGE_KIND_APS_MULTISOURCE_ADMISSION}' must be complete before APS export-package handoff"
        )
    source_summary = dict(source_row.summary_json or {})
    if str(source_summary.get("aps_target_family") or "").strip() != "multisource_admission":
        raise Layer3ApsReportExportPackageHandoffError(
            f"Layer 3 package '{PACKAGE_KIND_APS_MULTISOURCE_ADMISSION}' does not point at the multisource APS family"
        )
    if str(source_summary.get("grouping_contract_id") or "").strip() != APS_MULTISOURCE_GROUPING_CONTRACT_ID:
        raise Layer3ApsReportExportPackageHandoffError(
            f"Layer 3 package '{PACKAGE_KIND_APS_MULTISOURCE_ADMISSION}' has incompatible multisource provenance"
        )
    source_ref = _require_existing_ref(
        source_row.payload_ref,
        label=f"Layer 3 package '{PACKAGE_KIND_APS_MULTISOURCE_ADMISSION}' payload ref",
    )
    try:
        admission_payload = json.loads(Path(source_ref).read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise Layer3ApsReportExportPackageHandoffError(
            f"Layer 3 package '{PACKAGE_KIND_APS_MULTISOURCE_ADMISSION}' payload ref is not valid JSON"
        ) from exc
    if str(admission_payload.get("schema_id") or "").strip() != APS_MULTISOURCE_SCHEMA_ID:
        raise Layer3ApsReportExportPackageHandoffError(
            f"Layer 3 package '{PACKAGE_KIND_APS_MULTISOURCE_ADMISSION}' has incompatible payload schema provenance"
        )
    admitted_groups = [dict(item or {}) for item in list(admission_payload.get("admitted_groups") or []) if isinstance(item, dict)]
    if len(admitted_groups) != 1:
        raise Layer3ApsReportExportPackageHandoffError(
            "APS export-package handoff requires exactly one admitted multisource group on existing Layer 3 durable surfaces"
        )
    admitted_group = admitted_groups[0]
    source_rows = [dict(item or {}) for item in list(admitted_group.get("sources") or []) if isinstance(item, dict)]
    if len(source_rows) < aps_export_package_contract.APS_EVIDENCE_REPORT_EXPORT_PACKAGE_MIN_SOURCES:
        raise Layer3ApsReportExportPackageHandoffError(
            "APS export-package handoff requires at least two admitted APS sources"
        )
    owner_run_ids = [str(item).strip() for item in list(admission_payload.get("owner_run_ids_json") or []) if str(item).strip()]
    if len(owner_run_ids) != 1:
        raise Layer3ApsReportExportPackageHandoffError(
            "APS export-package handoff requires exactly one owner run id across the admitted multisource package"
        )
    reconciliation_record_id = str(source_row.reconciliation_record_id or "").strip()
    reconciliation = db.get(L3ReconciliationRecord, reconciliation_record_id)
    if reconciliation is None or reconciliation.session_id != session_id:
        raise Layer3ApsReportExportPackageHandoffError(
            f"Layer 3 session '{session_id}' is missing reconciliation provenance required for APS export-package handoff"
        )
    return source_row, reconciliation, admission_payload, admitted_group


def _candidate_export_paths(*, owner_run_id: str) -> list[Path]:
    reports_dir = Path(settings.connector_reports_dir)
    scope = aps_report_export.evidence_report_export_scope(owner_run_id)
    return sorted(reports_dir.glob(f"{scope}_*_aps_evidence_report_export_v1.json"), key=lambda path: path.name)


def _admitted_key_or_raise(source_row: dict[str, Any]) -> tuple[str, str]:
    target_id = str(source_row.get("target_id") or "").strip()
    content_id = str(source_row.get("content_id") or "").strip()
    if not target_id or not content_id:
        raise Layer3ApsReportExportPackageHandoffError(
            "APS export-package handoff requires admitted multisource sources with target_id and content_id"
        )
    return target_id, content_id


def _load_export_with_report_or_raise(candidate_path: Path) -> tuple[dict[str, Any], dict[str, Any]]:
    try:
        export_payload, _export_path = aps_report_export.load_persisted_evidence_report_export_artifact(
            evidence_report_export_ref=candidate_path
        )
    except aps_report_export.EvidenceReportExportError as exc:
        raise Layer3ApsReportExportPackageHandoffError(
            f"APS export-package handoff failed ({exc.code}): {exc.message or str(exc)}"
        ) from exc
    source_report_ref = _require_existing_ref(
        str(dict(export_payload.get("source_evidence_report") or {}).get("evidence_report_ref") or ""),
        label=f"APS evidence-report-export '{candidate_path.name}' source evidence report ref",
    )
    try:
        source_report_payload, _report_path = aps_report.load_persisted_evidence_report_artifact(
            evidence_report_ref=source_report_ref
        )
    except aps_report.EvidenceReportError as exc:
        raise Layer3ApsReportExportPackageHandoffError(
            f"APS export-package handoff failed ({exc.code}): {exc.message or str(exc)}"
        ) from exc
    return export_payload, source_report_payload


def _candidate_source_key(
    *,
    source_report_payload: dict[str, Any],
    owner_run_id: str,
) -> tuple[str, str] | None:
    sections = [dict(item or {}) for item in list(source_report_payload.get("sections") or []) if isinstance(item, dict)]
    if not sections:
        return None
    run_ids = {str(section.get("run_id") or "").strip() for section in sections}
    if run_ids != {owner_run_id}:
        return None
    source_keys: set[tuple[str, str]] = set()
    for section in sections:
        target_id = str(section.get("target_id") or "").strip()
        content_id = str(section.get("content_id") or "").strip()
        if not target_id or not content_id:
            return None
        source_keys.add((target_id, content_id))
    if len(source_keys) != 1:
        return None
    return next(iter(source_keys))


def _resolve_source_exports_or_raise(
    *,
    admitted_group: dict[str, Any],
) -> tuple[str, list[dict[str, Any]], list[str]]:
    owner_run_id = str(admitted_group.get("owner_run_id") or "").strip()
    if not owner_run_id:
        raise Layer3ApsReportExportPackageHandoffError(
            "APS export-package handoff requires an admitted multisource group with owner_run_id"
        )
    source_rows = [dict(item or {}) for item in list(admitted_group.get("sources") or []) if isinstance(item, dict)]
    admitted_key_order = [_admitted_key_or_raise(source_row) for source_row in source_rows]

    candidate_map: dict[tuple[str, str], tuple[dict[str, Any], str]] = {}
    for candidate_path in _candidate_export_paths(owner_run_id=owner_run_id):
        export_payload, source_report_payload = _load_export_with_report_or_raise(candidate_path)
        source_key = _candidate_source_key(
            source_report_payload=source_report_payload,
            owner_run_id=owner_run_id,
        )
        if source_key is None or source_key not in admitted_key_order:
            continue
        if source_key in candidate_map:
            raise Layer3ApsReportExportPackageHandoffError(
                f"APS export-package handoff found multiple persisted exports for admitted source identity '{source_key[0]}:{source_key[1]}'"
            )
        candidate_map[source_key] = (export_payload, str(candidate_path))

    export_payloads: list[dict[str, Any]] = []
    export_refs: list[str] = []
    for target_id, content_id in admitted_key_order:
        match = candidate_map.get((target_id, content_id))
        if match is None:
            raise Layer3ApsReportExportPackageHandoffError(
                f"APS export-package handoff could not resolve a persisted export for admitted source identity '{target_id}:{content_id}'"
            )
        export_payloads.append(match[0])
        export_refs.append(match[1])
    return owner_run_id, export_payloads, export_refs


def _materialize_export_package_or_raise(
    *,
    admitted_group: dict[str, Any],
) -> tuple[dict[str, Any], str, list[str]]:
    owner_run_id, export_payloads, export_refs = _resolve_source_exports_or_raise(admitted_group=admitted_group)
    try:
        package_payload = aps_export_package_contract.build_evidence_report_export_package_payload(
            export_payloads,
            generated_at_utc=_utc_iso(),
            owner_run_id=owner_run_id,
        )
        artifact_path = aps_export_package.evidence_report_export_package_artifact_path(
            owner_run_id=owner_run_id,
            evidence_report_export_package_id=str(
                package_payload.get("evidence_report_export_package_id") or ""
            ),
            reports_dir=settings.connector_reports_dir,
        )
        validated_payload, package_ref = aps_export_package._persist_or_validate_evidence_report_export_package(
            artifact_path=artifact_path,
            payload=package_payload,
        )
    except ValueError as exc:
        raise Layer3ApsReportExportPackageHandoffError(
            f"APS export-package handoff failed ({str(exc) or 'invalid_request'}): {str(exc)}"
        ) from exc
    except aps_export_package.EvidenceReportExportPackageError as exc:
        raise Layer3ApsReportExportPackageHandoffError(
            f"APS export-package handoff failed ({exc.code}): {exc.message or str(exc)}"
        ) from exc
    return validated_payload, str(
        validated_payload.get("_evidence_report_export_package_ref") or package_ref
    ), export_refs


def _summary_json(
    *,
    source_row: L3OutputPackage,
    admitted_group: dict[str, Any],
    package_payload: dict[str, Any],
    package_ref: str,
    export_refs: list[str],
) -> dict[str, Any]:
    source_exports = [dict(item or {}) for item in list(package_payload.get("source_exports") or []) if isinstance(item, dict)]
    return {
        "package_kind": PACKAGE_KIND_APS_EVIDENCE_REPORT_EXPORT_PACKAGE_HANDOFF,
        "package_status": source_row.status,
        "source_gate": SOURCE_GATE_D_APS_EXPORT_PACKAGE_FREEZE,
        "schema_id": APS_REPORT_EXPORT_PACKAGE_HANDOFF_SCHEMA_ID,
        "schema_version": APS_REPORT_EXPORT_PACKAGE_HANDOFF_SCHEMA_VERSION,
        "aps_target_family": "evidence_report_export_package",
        "aps_schema_id": aps_export_package_contract.APS_EVIDENCE_REPORT_EXPORT_PACKAGE_SCHEMA_ID,
        "evidence_report_export_package_id": str(
            package_payload.get("evidence_report_export_package_id") or ""
        ),
        "evidence_report_export_package_ref": package_ref,
        "evidence_report_export_package_checksum": str(
            package_payload.get("evidence_report_export_package_checksum") or ""
        ),
        "owner_run_id": str(package_payload.get("owner_run_id") or ""),
        "admission_group_id": str(admitted_group.get("admission_group_id") or ""),
        "source_export_count": int(package_payload.get("source_export_count") or 0),
        "ordered_source_exports_sha256": str(
            package_payload.get("ordered_source_exports_sha256") or ""
        ),
        "source_export_ids_json": [
            str(item.get("evidence_report_export_id") or "") for item in source_exports
        ],
        "source_export_refs_json": list(export_refs),
        "source_package_kinds_json": [PACKAGE_KIND_APS_MULTISOURCE_ADMISSION],
        "source_package_refs_json": {
            PACKAGE_KIND_APS_MULTISOURCE_ADMISSION: str(source_row.payload_ref or ""),
        },
        "compatibility_notes_json": [
            "aps_evidence_report_export_package_handoff points at a persisted aps.evidence_report_export_package.v1 artifact",
            "aps_multisource_admission remains the required Layer 3 source package for this tranche",
            "report-export package contract, checksum, and gate semantics are reused without widening",
            "persisted same-run exports are matched back to admitted source identities through source evidence report refs",
            "connector-run runtime refs remain untouched in this Layer 3 handoff path",
        ],
        "field_map_json": {
            "aps_multisource_admission.admitted_groups[0].sources[].target_id": "source_exports[].source_evidence_report.sections[].target_id",
            "aps_multisource_admission.admitted_groups[0].sources[].content_id": "source_exports[].source_evidence_report.sections[].content_id",
            "source_exports[].evidence_report_export_ref": "source_exports[].evidence_report_export_ref",
            "source_exports[].evidence_report_export_checksum": "source_exports[].evidence_report_export_checksum",
            "source_exports[].source_evidence_report_ref": "source_exports[].source_evidence_report_ref",
        },
        "handoff_status": {
            "status": "aps_evidence_report_export_package_emitted",
            "aps_multisource_admitted": True,
            "evidence_report_export_package_handoff_admitted": True,
            "evidence_report_export_package_persisted": True,
            "runtime_db_writes_performed": False,
            "owner_run_id": str(package_payload.get("owner_run_id") or ""),
            "admission_group_id": str(admitted_group.get("admission_group_id") or ""),
            "source_export_count": int(package_payload.get("source_export_count") or 0),
            "ordered_source_exports_sha256": str(
                package_payload.get("ordered_source_exports_sha256") or ""
            ),
            "total_sections": int(package_payload.get("total_sections") or 0),
            "total_citations": int(package_payload.get("total_citations") or 0),
            "total_groups": int(package_payload.get("total_groups") or 0),
        },
    }


def materialize_aps_report_export_package_handoff(
    db: Session,
    *,
    session_id: str,
) -> Layer3ApsReportExportPackageHandoffResult:
    session = _load_session_or_raise(db, session_id=session_id)
    source_row, reconciliation, _admission_payload, admitted_group = _load_source_package_or_raise(
        db,
        session_id=session.session_id,
    )
    package_payload, package_ref, export_refs = _materialize_export_package_or_raise(
        admitted_group=admitted_group,
    )
    output_package = L3OutputPackage(
        output_package_id=uuid_str(),
        session_id=session.session_id,
        reconciliation_record_id=reconciliation.reconciliation_record_id,
        package_kind=PACKAGE_KIND_APS_EVIDENCE_REPORT_EXPORT_PACKAGE_HANDOFF,
        status=source_row.status,
        payload_ref=package_ref,
        payload_hash=hashlib.sha256(Path(package_ref).read_bytes()).hexdigest(),
        summary_json=_summary_json(
            source_row=source_row,
            admitted_group=admitted_group,
            package_payload=package_payload,
            package_ref=package_ref,
            export_refs=export_refs,
        ),
    )
    db.add(output_package)
    db.flush()
    return Layer3ApsReportExportPackageHandoffResult(
        output_package=output_package,
        evidence_report_export_package_payload=package_payload,
    )
