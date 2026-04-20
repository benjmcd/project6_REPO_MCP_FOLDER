from __future__ import annotations

import hashlib
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.models import L3OutputPackage, L3ReconciliationRecord, L3Session, uuid_str
from app.services import nrc_aps_evidence_report as aps_report
from app.services import nrc_aps_evidence_report_contract as aps_report_contract
from app.services import nrc_aps_evidence_report_export as aps_report_export
from app.services import nrc_aps_evidence_report_export_contract as aps_report_export_contract
from app.services.layer3_aps_report_handoff import PACKAGE_KIND_APS_EVIDENCE_REPORT_HANDOFF
from app.services.layer3_package_entry import (
    PACKAGE_STATUS_COMPLETE,
    PACKAGE_STATUS_COMPLETE_WITH_WARNINGS,
)
from app.services.layer3_session_entry import (
    SESSION_STATUS_COMPLETED,
    SESSION_STATUS_COMPLETED_WITH_WARNINGS,
    SESSION_STATUS_FAILED,
)


PACKAGE_KIND_APS_EVIDENCE_REPORT_EXPORT_HANDOFF = "aps_evidence_report_export_handoff"
APS_REPORT_EXPORT_HANDOFF_SCHEMA_ID = "layer3.aps_evidence_report_export_handoff.v1"
APS_REPORT_EXPORT_HANDOFF_SCHEMA_VERSION = 1
SOURCE_GATE_D_APS_REPORT_EXPORT_FREEZE = "12_GATED_APS_REPORT_EXPORT_FREEZE"

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


class Layer3ApsReportExportHandoffError(ValueError):
    pass


@dataclass(frozen=True)
class Layer3ApsReportExportHandoffResult:
    output_package: L3OutputPackage
    evidence_report_export_payload: dict[str, Any]


def _utc_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _require_existing_ref(ref: str | None, *, label: str) -> str:
    normalized = str(ref or "").strip()
    if not normalized:
        raise Layer3ApsReportExportHandoffError(f"{label} is missing")
    if not Path(normalized).exists():
        raise Layer3ApsReportExportHandoffError(f"{label} does not exist: {normalized}")
    return normalized


def _load_session_or_raise(db: Session, *, session_id: str) -> L3Session:
    session = db.get(L3Session, session_id)
    if session is None:
        raise Layer3ApsReportExportHandoffError(f"Layer 3 session '{session_id}' was not found")
    if session.status not in TERMINAL_SESSION_STATUSES or session.completed_at is None:
        raise Layer3ApsReportExportHandoffError(
            f"Layer 3 session '{session_id}' must be terminal before Gate D APS report-export handoff"
        )
    return session


def _load_source_package_or_raise(
    db: Session,
    *,
    session_id: str,
) -> tuple[L3OutputPackage, L3ReconciliationRecord]:
    rows = (
        db.query(L3OutputPackage)
        .filter(L3OutputPackage.session_id == session_id)
        .order_by(L3OutputPackage.package_kind.asc())
        .all()
    )
    rows_by_kind = {row.package_kind: row for row in rows}
    if PACKAGE_KIND_APS_EVIDENCE_REPORT_EXPORT_HANDOFF in rows_by_kind:
        raise Layer3ApsReportExportHandoffError(
            f"Layer 3 session '{session_id}' already has an APS evidence-report-export handoff package"
        )
    source_row = rows_by_kind.get(PACKAGE_KIND_APS_EVIDENCE_REPORT_HANDOFF)
    if source_row is None:
        raise Layer3ApsReportExportHandoffError(
            f"Layer 3 session '{session_id}' is missing the APS evidence-report handoff package required for APS report-export handoff"
        )
    if source_row.status not in ACCEPTED_SOURCE_PACKAGE_STATUSES:
        raise Layer3ApsReportExportHandoffError(
            f"Layer 3 package '{PACKAGE_KIND_APS_EVIDENCE_REPORT_HANDOFF}' must be complete before APS report-export handoff"
        )
    source_summary = dict(source_row.summary_json or {})
    if str(source_summary.get("aps_target_family") or "").strip() != "evidence_report":
        raise Layer3ApsReportExportHandoffError(
            f"Layer 3 package '{PACKAGE_KIND_APS_EVIDENCE_REPORT_HANDOFF}' does not point at the evidence-report APS family"
        )
    if (
        str(source_summary.get("aps_schema_id") or "").strip()
        != aps_report_contract.APS_EVIDENCE_REPORT_SCHEMA_ID
    ):
        raise Layer3ApsReportExportHandoffError(
            f"Layer 3 package '{PACKAGE_KIND_APS_EVIDENCE_REPORT_HANDOFF}' has incompatible APS schema provenance"
        )
    _require_existing_ref(
        source_row.payload_ref,
        label=f"Layer 3 package '{PACKAGE_KIND_APS_EVIDENCE_REPORT_HANDOFF}' payload ref",
    )
    reconciliation_record_id = str(source_row.reconciliation_record_id or "").strip()
    reconciliation = db.get(L3ReconciliationRecord, reconciliation_record_id)
    if reconciliation is None or reconciliation.session_id != session_id:
        raise Layer3ApsReportExportHandoffError(
            f"Layer 3 session '{session_id}' is missing reconciliation provenance required for APS report-export handoff"
        )
    return source_row, reconciliation


def _materialize_evidence_report_export_or_raise(
    source_row: L3OutputPackage,
) -> tuple[dict[str, Any], str]:
    source_report_ref = _require_existing_ref(
        source_row.payload_ref,
        label=f"Layer 3 package '{PACKAGE_KIND_APS_EVIDENCE_REPORT_HANDOFF}' payload ref",
    )
    try:
        source_report_payload, _source_path = aps_report.load_persisted_evidence_report_artifact(
            evidence_report_ref=source_report_ref
        )
        source_report_summary = aps_report_export_contract.source_evidence_report_summary_payload(
            source_report_payload
        )
        source_citation_pack = dict(source_report_summary.get("source_citation_pack") or {})
        source_bundle = dict(source_citation_pack.get("source_bundle") or {})
        effective_run_id = str(source_bundle.get("run_id") or "").strip()
        if not effective_run_id:
            raise Layer3ApsReportExportHandoffError(
                "APS evidence-report-export handoff requires a source evidence report with run_id"
            )
        export_payload = aps_report_export_contract.build_evidence_report_export_payload(
            source_report_payload,
            generated_at_utc=_utc_iso(),
        )
        evidence_report_export_id = str(export_payload.get("evidence_report_export_id") or "").strip()
        artifact_path = aps_report_export.evidence_report_export_artifact_path(
            run_id=effective_run_id,
            evidence_report_export_id=evidence_report_export_id,
            reports_dir=settings.connector_reports_dir,
        )
        validated_payload, evidence_report_export_ref = (
            aps_report_export._persist_or_validate_evidence_report_export(
                artifact_path=artifact_path,
                payload=export_payload,
            )
        )
        loaded_payload, _persisted_path = aps_report_export.load_persisted_evidence_report_export_artifact(
            evidence_report_export_ref=evidence_report_export_ref
        )
    except aps_report.EvidenceReportError as exc:
        raise Layer3ApsReportExportHandoffError(
            f"APS evidence-report-export handoff failed ({exc.code}): {exc.message or str(exc)}"
        ) from exc
    except aps_report_export.EvidenceReportExportError as exc:
        raise Layer3ApsReportExportHandoffError(
            f"APS evidence-report-export handoff failed ({exc.code}): {exc.message or str(exc)}"
        ) from exc
    return loaded_payload or validated_payload, str(
        loaded_payload.get("_evidence_report_export_ref") or evidence_report_export_ref
    )


def _summary_json(
    *,
    source_row: L3OutputPackage,
    evidence_report_export_payload: dict[str, Any],
    evidence_report_export_ref: str,
) -> dict[str, Any]:
    source_report = dict(evidence_report_export_payload.get("source_evidence_report") or {})
    source_citation_pack = dict(source_report.get("source_citation_pack") or {})
    source_bundle = dict(source_citation_pack.get("source_bundle") or {})
    return {
        "package_kind": PACKAGE_KIND_APS_EVIDENCE_REPORT_EXPORT_HANDOFF,
        "package_status": source_row.status,
        "source_gate": SOURCE_GATE_D_APS_REPORT_EXPORT_FREEZE,
        "schema_id": APS_REPORT_EXPORT_HANDOFF_SCHEMA_ID,
        "schema_version": APS_REPORT_EXPORT_HANDOFF_SCHEMA_VERSION,
        "aps_target_family": "evidence_report_export",
        "aps_schema_id": aps_report_export_contract.APS_EVIDENCE_REPORT_EXPORT_SCHEMA_ID,
        "evidence_report_export_id": str(
            evidence_report_export_payload.get("evidence_report_export_id") or ""
        ),
        "evidence_report_export_ref": evidence_report_export_ref,
        "evidence_report_export_checksum": str(
            evidence_report_export_payload.get("evidence_report_export_checksum") or ""
        ),
        "source_package_kinds_json": [PACKAGE_KIND_APS_EVIDENCE_REPORT_HANDOFF],
        "source_package_refs_json": {
            PACKAGE_KIND_APS_EVIDENCE_REPORT_HANDOFF: str(source_row.payload_ref or ""),
        },
        "compatibility_notes_json": [
            "aps_evidence_report_export_handoff points at a persisted aps.evidence_report_export.v1 artifact",
            "aps_evidence_report_handoff remains the required source package for this tranche",
            "evidence-report-export contract, checksum, and gate semantics are reused without widening",
            "connector-run runtime refs remain untouched in this Layer 3 handoff path",
        ],
        "field_map_json": {
            "aps_evidence_report_handoff.payload_ref": "source_evidence_report.evidence_report_ref",
            "source_evidence_report.evidence_report_id": "source_evidence_report.evidence_report_id",
            "source_evidence_report.evidence_report_checksum": "source_evidence_report.evidence_report_checksum",
            "source_evidence_report.source_citation_pack.source_bundle.run_id": "source_evidence_report.source_citation_pack.source_bundle.run_id",
            "rendered_markdown": "rendered_markdown",
            "rendered_markdown_sha256": "rendered_markdown_sha256",
        },
        "handoff_status": {
            "status": "aps_evidence_report_export_emitted",
            "aps_handoff_admitted": True,
            "evidence_report_export_handoff_admitted": True,
            "evidence_report_export_persisted": True,
            "runtime_db_writes_performed": False,
            "section_count": int(evidence_report_export_payload.get("total_sections") or 0),
            "citation_count": int(evidence_report_export_payload.get("total_citations") or 0),
            "group_count": int(evidence_report_export_payload.get("total_groups") or 0),
            "source_run_id": str(source_bundle.get("run_id") or ""),
            "source_evidence_report_id": str(source_report.get("evidence_report_id") or ""),
            "source_evidence_report_checksum": str(
                source_report.get("evidence_report_checksum") or ""
            ),
            "source_evidence_report_ref": str(source_report.get("evidence_report_ref") or ""),
            "source_citation_pack_id": str(source_citation_pack.get("citation_pack_id") or ""),
        },
    }


def materialize_aps_report_export_handoff(
    db: Session,
    *,
    session_id: str,
) -> Layer3ApsReportExportHandoffResult:
    session = _load_session_or_raise(db, session_id=session_id)
    source_row, reconciliation = _load_source_package_or_raise(db, session_id=session.session_id)
    evidence_report_export_payload, evidence_report_export_ref = (
        _materialize_evidence_report_export_or_raise(source_row)
    )
    output_package = L3OutputPackage(
        output_package_id=uuid_str(),
        session_id=session.session_id,
        reconciliation_record_id=reconciliation.reconciliation_record_id,
        package_kind=PACKAGE_KIND_APS_EVIDENCE_REPORT_EXPORT_HANDOFF,
        status=source_row.status,
        payload_ref=evidence_report_export_ref,
        payload_hash=hashlib.sha256(Path(evidence_report_export_ref).read_bytes()).hexdigest(),
        summary_json=_summary_json(
            source_row=source_row,
            evidence_report_export_payload=evidence_report_export_payload,
            evidence_report_export_ref=evidence_report_export_ref,
        ),
    )
    db.add(output_package)
    db.flush()
    return Layer3ApsReportExportHandoffResult(
        output_package=output_package,
        evidence_report_export_payload=evidence_report_export_payload,
    )
