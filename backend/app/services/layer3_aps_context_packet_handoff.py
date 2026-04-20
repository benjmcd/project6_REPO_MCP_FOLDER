from __future__ import annotations

import hashlib
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.models import L3OutputPackage, L3ReconciliationRecord, L3Session, uuid_str
from app.services import nrc_aps_context_packet as aps_context_packet
from app.services import nrc_aps_context_packet_contract as aps_context_contract
from app.services import nrc_aps_evidence_report_export as aps_report_export
from app.services import nrc_aps_evidence_report_export_contract as aps_report_export_contract
from app.services.layer3_aps_report_export_handoff import PACKAGE_KIND_APS_EVIDENCE_REPORT_EXPORT_HANDOFF
from app.services.layer3_package_entry import (
    PACKAGE_STATUS_COMPLETE,
    PACKAGE_STATUS_COMPLETE_WITH_WARNINGS,
)
from app.services.layer3_session_entry import (
    SESSION_STATUS_COMPLETED,
    SESSION_STATUS_COMPLETED_WITH_WARNINGS,
    SESSION_STATUS_FAILED,
)


PACKAGE_KIND_APS_CONTEXT_PACKET_HANDOFF = "aps_context_packet_handoff"
APS_CONTEXT_PACKET_HANDOFF_SCHEMA_ID = "layer3.aps_context_packet_handoff.v1"
APS_CONTEXT_PACKET_HANDOFF_SCHEMA_VERSION = 1
SOURCE_GATE_D_APS_CONTEXT_FREEZE = "13_GATED_APS_CONTEXT_FREEZE"

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


class Layer3ApsContextPacketHandoffError(ValueError):
    pass


@dataclass(frozen=True)
class Layer3ApsContextPacketHandoffResult:
    output_package: L3OutputPackage
    context_packet_payload: dict[str, Any]


def _utc_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _require_existing_ref(ref: str | None, *, label: str) -> str:
    normalized = str(ref or "").strip()
    if not normalized:
        raise Layer3ApsContextPacketHandoffError(f"{label} is missing")
    if not Path(normalized).exists():
        raise Layer3ApsContextPacketHandoffError(f"{label} does not exist: {normalized}")
    return normalized


def _load_session_or_raise(db: Session, *, session_id: str) -> L3Session:
    session = db.get(L3Session, session_id)
    if session is None:
        raise Layer3ApsContextPacketHandoffError(f"Layer 3 session '{session_id}' was not found")
    if session.status not in TERMINAL_SESSION_STATUSES or session.completed_at is None:
        raise Layer3ApsContextPacketHandoffError(
            f"Layer 3 session '{session_id}' must be terminal before Gate D APS context-packet handoff"
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
    if PACKAGE_KIND_APS_CONTEXT_PACKET_HANDOFF in rows_by_kind:
        raise Layer3ApsContextPacketHandoffError(
            f"Layer 3 session '{session_id}' already has an APS context-packet handoff package"
        )
    source_row = rows_by_kind.get(PACKAGE_KIND_APS_EVIDENCE_REPORT_EXPORT_HANDOFF)
    if source_row is None:
        raise Layer3ApsContextPacketHandoffError(
            f"Layer 3 session '{session_id}' is missing the APS evidence-report-export handoff package required for APS context-packet handoff"
        )
    if source_row.status not in ACCEPTED_SOURCE_PACKAGE_STATUSES:
        raise Layer3ApsContextPacketHandoffError(
            f"Layer 3 package '{PACKAGE_KIND_APS_EVIDENCE_REPORT_EXPORT_HANDOFF}' must be complete before APS context-packet handoff"
        )
    source_summary = dict(source_row.summary_json or {})
    if str(source_summary.get("aps_target_family") or "").strip() != "evidence_report_export":
        raise Layer3ApsContextPacketHandoffError(
            f"Layer 3 package '{PACKAGE_KIND_APS_EVIDENCE_REPORT_EXPORT_HANDOFF}' does not point at the evidence-report-export APS family"
        )
    if (
        str(source_summary.get("aps_schema_id") or "").strip()
        != aps_report_export_contract.APS_EVIDENCE_REPORT_EXPORT_SCHEMA_ID
    ):
        raise Layer3ApsContextPacketHandoffError(
            f"Layer 3 package '{PACKAGE_KIND_APS_EVIDENCE_REPORT_EXPORT_HANDOFF}' has incompatible APS schema provenance"
        )
    _require_existing_ref(
        source_row.payload_ref,
        label=f"Layer 3 package '{PACKAGE_KIND_APS_EVIDENCE_REPORT_EXPORT_HANDOFF}' payload ref",
    )
    reconciliation_record_id = str(source_row.reconciliation_record_id or "").strip()
    reconciliation = db.get(L3ReconciliationRecord, reconciliation_record_id)
    if reconciliation is None or reconciliation.session_id != session_id:
        raise Layer3ApsContextPacketHandoffError(
            f"Layer 3 session '{session_id}' is missing reconciliation provenance required for APS context-packet handoff"
        )
    return source_row, reconciliation


def _materialize_context_packet_or_raise(
    source_row: L3OutputPackage,
) -> tuple[dict[str, Any], str]:
    source_export_ref = _require_existing_ref(
        source_row.payload_ref,
        label=f"Layer 3 package '{PACKAGE_KIND_APS_EVIDENCE_REPORT_EXPORT_HANDOFF}' payload ref",
    )
    try:
        source_export_payload, _source_path = aps_report_export.load_persisted_evidence_report_export_artifact(
            evidence_report_export_ref=source_export_ref
        )
        context_packet_payload = aps_context_contract.build_context_packet_payload(
            source_family=aps_context_contract.APS_CONTEXT_PACKET_SOURCE_FAMILY_EXPORT,
            source_payload=source_export_payload,
            generated_at_utc=_utc_iso(),
        )
        source_descriptor = dict(context_packet_payload.get("source_descriptor") or {})
        owner_run_id = str(source_descriptor.get("owner_run_id") or "").strip()
        if not owner_run_id:
            raise Layer3ApsContextPacketHandoffError(
                "APS context-packet handoff requires a source evidence-report-export with owner run id"
            )
        artifact_path = aps_context_packet.context_packet_artifact_path(
            owner_run_id=owner_run_id,
            context_packet_id=str(context_packet_payload.get("context_packet_id") or ""),
            reports_dir=settings.connector_reports_dir,
        )
        validated_payload, context_packet_ref = aps_context_packet._persist_or_validate_context_packet(
            artifact_path=artifact_path,
            payload=context_packet_payload,
        )
        loaded_payload, _persisted_path = aps_context_packet.load_persisted_context_packet_artifact(
            context_packet_ref=context_packet_ref
        )
    except aps_report_export.EvidenceReportExportError as exc:
        raise Layer3ApsContextPacketHandoffError(
            f"APS context-packet handoff failed ({exc.code}): {exc.message or str(exc)}"
        ) from exc
    except aps_context_packet.ContextPacketError as exc:
        raise Layer3ApsContextPacketHandoffError(
            f"APS context-packet handoff failed ({exc.code}): {exc.message or str(exc)}"
        ) from exc
    return loaded_payload or validated_payload, str(
        loaded_payload.get("_context_packet_ref") or context_packet_ref
    )


def _summary_json(
    *,
    source_row: L3OutputPackage,
    context_packet_payload: dict[str, Any],
    context_packet_ref: str,
) -> dict[str, Any]:
    source_descriptor = dict(context_packet_payload.get("source_descriptor") or {})
    return {
        "package_kind": PACKAGE_KIND_APS_CONTEXT_PACKET_HANDOFF,
        "package_status": source_row.status,
        "source_gate": SOURCE_GATE_D_APS_CONTEXT_FREEZE,
        "schema_id": APS_CONTEXT_PACKET_HANDOFF_SCHEMA_ID,
        "schema_version": APS_CONTEXT_PACKET_HANDOFF_SCHEMA_VERSION,
        "aps_target_family": "context_packet",
        "aps_schema_id": aps_context_contract.APS_CONTEXT_PACKET_SCHEMA_ID,
        "context_packet_id": str(context_packet_payload.get("context_packet_id") or ""),
        "context_packet_ref": context_packet_ref,
        "context_packet_checksum": str(context_packet_payload.get("context_packet_checksum") or ""),
        "source_package_kinds_json": [PACKAGE_KIND_APS_EVIDENCE_REPORT_EXPORT_HANDOFF],
        "source_package_refs_json": {
            PACKAGE_KIND_APS_EVIDENCE_REPORT_EXPORT_HANDOFF: str(source_row.payload_ref or ""),
        },
        "compatibility_notes_json": [
            "aps_context_packet_handoff points at a persisted aps.context_packet.v1 artifact",
            "aps_evidence_report_export_handoff remains the required source package for this tranche",
            "context-packet contract, checksum, and gate semantics are reused without widening",
            "source_family=evidence_report_export remains fixed for this Layer 3 handoff path",
            "connector-run runtime refs remain untouched in this Layer 3 handoff path",
        ],
        "field_map_json": {
            "aps_evidence_report_export_handoff.payload_ref": "source_descriptor.source_ref",
            "source_descriptor.source_id": "source_descriptor.source_id",
            "source_descriptor.source_checksum": "source_descriptor.source_checksum",
            "source_descriptor.owner_run_id": "source_descriptor.owner_run_id",
            "facts[].fact_type": "facts[].fact_type",
            "caveats[].code": "caveats[].code",
            "constraints[].code": "constraints[].code",
            "unresolved_questions[].code": "unresolved_questions[].code",
        },
        "handoff_status": {
            "status": "aps_context_packet_emitted",
            "aps_handoff_admitted": True,
            "context_packet_handoff_admitted": True,
            "context_packet_persisted": True,
            "runtime_db_writes_performed": False,
            "source_family": str(context_packet_payload.get("source_family") or ""),
            "fact_count": int(context_packet_payload.get("total_facts") or 0),
            "caveat_count": int(context_packet_payload.get("total_caveats") or 0),
            "constraint_count": int(context_packet_payload.get("total_constraints") or 0),
            "unresolved_question_count": int(
                context_packet_payload.get("total_unresolved_questions") or 0
            ),
            "source_run_id": str(source_descriptor.get("owner_run_id") or ""),
            "source_evidence_report_export_id": str(source_descriptor.get("source_id") or ""),
            "source_evidence_report_export_checksum": str(
                source_descriptor.get("source_checksum") or ""
            ),
            "source_evidence_report_export_ref": str(source_descriptor.get("source_ref") or ""),
            "source_evidence_report_id": str(source_descriptor.get("source_evidence_report_id") or ""),
            "source_evidence_report_checksum": str(
                source_descriptor.get("source_evidence_report_checksum") or ""
            ),
            "source_evidence_report_ref": str(
                source_descriptor.get("source_evidence_report_ref") or ""
            ),
        },
    }


def materialize_aps_context_packet_handoff(
    db: Session,
    *,
    session_id: str,
) -> Layer3ApsContextPacketHandoffResult:
    session = _load_session_or_raise(db, session_id=session_id)
    source_row, reconciliation = _load_source_package_or_raise(db, session_id=session.session_id)
    context_packet_payload, context_packet_ref = _materialize_context_packet_or_raise(source_row)
    output_package = L3OutputPackage(
        output_package_id=uuid_str(),
        session_id=session.session_id,
        reconciliation_record_id=reconciliation.reconciliation_record_id,
        package_kind=PACKAGE_KIND_APS_CONTEXT_PACKET_HANDOFF,
        status=source_row.status,
        payload_ref=context_packet_ref,
        payload_hash=hashlib.sha256(Path(context_packet_ref).read_bytes()).hexdigest(),
        summary_json=_summary_json(
            source_row=source_row,
            context_packet_payload=context_packet_payload,
            context_packet_ref=context_packet_ref,
        ),
    )
    db.add(output_package)
    db.flush()
    return Layer3ApsContextPacketHandoffResult(
        output_package=output_package,
        context_packet_payload=context_packet_payload,
    )
