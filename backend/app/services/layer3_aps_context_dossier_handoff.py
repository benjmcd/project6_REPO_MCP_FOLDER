from __future__ import annotations

import hashlib
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.models import L3OutputPackage, L3ReconciliationRecord, L3Session, uuid_str
from app.services import nrc_aps_context_dossier as aps_context_dossier
from app.services import nrc_aps_context_dossier_contract as aps_context_dossier_contract
from app.services import nrc_aps_context_packet as aps_context_packet
from app.services import nrc_aps_context_packet_contract as aps_context_packet_contract
from app.services import nrc_aps_evidence_report_export as aps_report_export
from app.services import nrc_aps_evidence_report_export_package as aps_export_package
from app.services import nrc_aps_evidence_report_export_package_contract as aps_export_package_contract
from app.services.layer3_aps_context_packet_package_handoff import (
    PACKAGE_KIND_APS_CONTEXT_PACKET_PACKAGE_HANDOFF,
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


PACKAGE_KIND_APS_CONTEXT_DOSSIER_HANDOFF = "aps_context_dossier_handoff"
APS_CONTEXT_DOSSIER_HANDOFF_SCHEMA_ID = "layer3.aps_context_dossier_handoff.v1"
APS_CONTEXT_DOSSIER_HANDOFF_SCHEMA_VERSION = 1
SOURCE_GATE_D_APS_CONTEXT_DOSSIER_FREEZE = "17_GATED_APS_CONTEXT_DOSSIER_FREEZE"

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


class Layer3ApsContextDossierHandoffError(ValueError):
    pass


@dataclass(frozen=True)
class Layer3ApsContextDossierHandoffResult:
    output_package: L3OutputPackage
    context_dossier_payload: dict[str, Any]


def _utc_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _require_existing_ref(ref: str | None, *, label: str) -> str:
    normalized = str(ref or "").strip()
    if not normalized:
        raise Layer3ApsContextDossierHandoffError(f"{label} is missing")
    if not Path(normalized).exists():
        raise Layer3ApsContextDossierHandoffError(f"{label} does not exist: {normalized}")
    return normalized


def _load_session_or_raise(db: Session, *, session_id: str) -> L3Session:
    session = db.get(L3Session, session_id)
    if session is None:
        raise Layer3ApsContextDossierHandoffError(f"Layer 3 session '{session_id}' was not found")
    if session.status not in TERMINAL_SESSION_STATUSES or session.completed_at is None:
        raise Layer3ApsContextDossierHandoffError(
            f"Layer 3 session '{session_id}' must be terminal before Gate D APS context-dossier handoff"
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
    if PACKAGE_KIND_APS_CONTEXT_DOSSIER_HANDOFF in rows_by_kind:
        raise Layer3ApsContextDossierHandoffError(
            f"Layer 3 session '{session_id}' already has an APS context-dossier handoff package"
        )
    source_row = rows_by_kind.get(PACKAGE_KIND_APS_CONTEXT_PACKET_PACKAGE_HANDOFF)
    if source_row is None:
        raise Layer3ApsContextDossierHandoffError(
            f"Layer 3 session '{session_id}' is missing the APS package-derived context handoff package required for APS context-dossier handoff"
        )
    if source_row.status not in ACCEPTED_SOURCE_PACKAGE_STATUSES:
        raise Layer3ApsContextDossierHandoffError(
            f"Layer 3 package '{PACKAGE_KIND_APS_CONTEXT_PACKET_PACKAGE_HANDOFF}' must be complete before APS context-dossier handoff"
        )
    source_summary = dict(source_row.summary_json or {})
    if str(source_summary.get("aps_target_family") or "").strip() != "context_packet_package":
        raise Layer3ApsContextDossierHandoffError(
            f"Layer 3 package '{PACKAGE_KIND_APS_CONTEXT_PACKET_PACKAGE_HANDOFF}' does not point at the package-derived APS context family"
        )
    if (
        str(source_summary.get("aps_schema_id") or "").strip()
        != aps_context_packet_contract.APS_CONTEXT_PACKET_SCHEMA_ID
    ):
        raise Layer3ApsContextDossierHandoffError(
            f"Layer 3 package '{PACKAGE_KIND_APS_CONTEXT_PACKET_PACKAGE_HANDOFF}' has incompatible APS schema provenance"
        )
    _require_existing_ref(
        source_row.payload_ref,
        label=f"Layer 3 package '{PACKAGE_KIND_APS_CONTEXT_PACKET_PACKAGE_HANDOFF}' payload ref",
    )
    reconciliation_record_id = str(source_row.reconciliation_record_id or "").strip()
    reconciliation = db.get(L3ReconciliationRecord, reconciliation_record_id)
    if reconciliation is None or reconciliation.session_id != session_id:
        raise Layer3ApsContextDossierHandoffError(
            f"Layer 3 session '{session_id}' is missing reconciliation provenance required for APS context-dossier handoff"
        )
    return source_row, reconciliation


def _load_package_context_payload_or_raise(source_row: L3OutputPackage) -> tuple[dict[str, Any], str]:
    source_packet_ref = _require_existing_ref(
        source_row.payload_ref,
        label=f"Layer 3 package '{PACKAGE_KIND_APS_CONTEXT_PACKET_PACKAGE_HANDOFF}' payload ref",
    )
    try:
        context_packet_payload, _context_packet_path = aps_context_packet.load_persisted_context_packet_artifact(
            context_packet_ref=source_packet_ref
        )
    except aps_context_packet.ContextPacketError as exc:
        raise Layer3ApsContextDossierHandoffError(
            f"APS context-dossier handoff failed ({exc.code}): {exc.message or str(exc)}"
        ) from exc
    if (
        str(context_packet_payload.get("source_family") or "").strip()
        != aps_context_packet_contract.APS_CONTEXT_PACKET_SOURCE_FAMILY_PACKAGE
    ):
        raise Layer3ApsContextDossierHandoffError(
            "APS context-dossier handoff requires the current package-derived context handoff package as the gating source row"
        )
    source_descriptor = dict(context_packet_payload.get("source_descriptor") or {})
    export_package_ref = _require_existing_ref(
        str(source_descriptor.get("source_ref") or ""),
        label="APS package-derived context handoff source export-package ref",
    )
    return context_packet_payload, export_package_ref


def _ordered_source_exports_or_raise(package_payload: dict[str, Any]) -> list[dict[str, Any]]:
    source_exports = [dict(item or {}) for item in list(package_payload.get("source_exports") or []) if isinstance(item, dict)]
    source_exports.sort(key=lambda item: int(item.get("export_ordinal") or 0))
    if len(source_exports) != 2:
        raise Layer3ApsContextDossierHandoffError(
            "APS context-dossier handoff requires exactly two persisted export-derived context packets in this tranche"
        )
    return source_exports


def _load_export_package_payload_or_raise(export_package_ref: str) -> dict[str, Any]:
    try:
        package_payload, _package_path = aps_export_package.load_persisted_evidence_report_export_package_artifact(
            evidence_report_export_package_ref=export_package_ref
        )
    except aps_export_package.EvidenceReportExportPackageError as exc:
        raise Layer3ApsContextDossierHandoffError(
            f"APS context-dossier handoff failed ({exc.code}): {exc.message or str(exc)}"
        ) from exc
    _ordered_source_exports_or_raise(package_payload)
    return package_payload


def _expected_export_context_packet_ref_or_raise(export_payload: dict[str, Any]) -> str:
    source_descriptor = aps_context_packet_contract.source_descriptor_payload(
        aps_context_packet_contract.APS_CONTEXT_PACKET_SOURCE_FAMILY_EXPORT,
        export_payload,
    )
    owner_run_id = str(source_descriptor.get("owner_run_id") or "").strip()
    source_id = str(source_descriptor.get("source_id") or "").strip()
    source_checksum = str(source_descriptor.get("source_checksum") or "").strip()
    if not owner_run_id or not source_id or not source_checksum:
        raise Layer3ApsContextDossierHandoffError(
            "APS context-dossier handoff requires export-derived source descriptors with owner_run_id, source_id, and source_checksum"
        )
    context_packet_id = aps_context_packet_contract.derive_context_packet_id(
        source_family=aps_context_packet_contract.APS_CONTEXT_PACKET_SOURCE_FAMILY_EXPORT,
        source_id=source_id,
        source_checksum=source_checksum,
    )
    return str(
        aps_context_packet.context_packet_artifact_path(
            owner_run_id=owner_run_id,
            context_packet_id=context_packet_id,
            reports_dir=settings.connector_reports_dir,
        )
    )


def _resolve_source_context_packets_or_raise(
    package_payload: dict[str, Any],
) -> tuple[str, list[dict[str, Any]], list[str], list[str]]:
    owner_run_id = str(package_payload.get("owner_run_id") or "").strip()
    if not owner_run_id:
        raise Layer3ApsContextDossierHandoffError(
            "APS context-dossier handoff requires a persisted export package with owner_run_id"
        )
    seen_context_packet_ids: set[str] = set()
    context_packet_payloads: list[dict[str, Any]] = []
    context_packet_refs: list[str] = []
    export_refs: list[str] = []
    for source_export in _ordered_source_exports_or_raise(package_payload):
        export_ref = _require_existing_ref(
            str(source_export.get("evidence_report_export_ref") or ""),
            label="APS export-package source export ref",
        )
        try:
            export_payload, _export_path = aps_report_export.load_persisted_evidence_report_export_artifact(
                evidence_report_export_ref=export_ref
            )
        except aps_report_export.EvidenceReportExportError as exc:
            raise Layer3ApsContextDossierHandoffError(
                f"APS context-dossier handoff failed ({exc.code}): {exc.message or str(exc)}"
            ) from exc
        packet_ref = _expected_export_context_packet_ref_or_raise(export_payload)
        if not Path(packet_ref).exists():
            raise Layer3ApsContextDossierHandoffError(
                f"APS context-dossier handoff could not resolve a persisted export-derived context packet for export ref '{export_ref}'"
            )
        try:
            context_packet_payload, _context_packet_path = aps_context_packet.load_persisted_context_packet_artifact(
                context_packet_ref=packet_ref
            )
        except aps_context_packet.ContextPacketError as exc:
            raise Layer3ApsContextDossierHandoffError(
                f"APS context-dossier handoff failed ({exc.code}): {exc.message or str(exc)}"
            ) from exc
        if (
            str(context_packet_payload.get("source_family") or "").strip()
            != aps_context_packet_contract.APS_CONTEXT_PACKET_SOURCE_FAMILY_EXPORT
        ):
            raise Layer3ApsContextDossierHandoffError(
                f"APS context-dossier handoff resolved a non-export context packet for export ref '{export_ref}'"
            )
        packet_descriptor = dict(context_packet_payload.get("source_descriptor") or {})
        if str(packet_descriptor.get("owner_run_id") or "").strip() != owner_run_id:
            raise Layer3ApsContextDossierHandoffError(
                "APS context-dossier handoff requires all export-derived context packets to share one owner_run_id"
            )
        if str(packet_descriptor.get("source_ref") or "").strip() != export_ref:
            raise Layer3ApsContextDossierHandoffError(
                f"APS context-dossier handoff resolved an export-derived context packet whose source ref does not match '{export_ref}'"
            )
        context_packet_id = str(context_packet_payload.get("context_packet_id") or "").strip()
        if context_packet_id in seen_context_packet_ids:
            raise Layer3ApsContextDossierHandoffError(
                f"APS context-dossier handoff resolved duplicate export-derived context packet identity '{context_packet_id}'"
            )
        seen_context_packet_ids.add(context_packet_id)
        context_packet_payloads.append(context_packet_payload)
        context_packet_refs.append(packet_ref)
        export_refs.append(export_ref)
    return owner_run_id, context_packet_payloads, context_packet_refs, export_refs


def _materialize_context_dossier_or_raise(
    source_row: L3OutputPackage,
) -> tuple[dict[str, Any], str, list[str], list[str], str]:
    package_context_payload, export_package_ref = _load_package_context_payload_or_raise(source_row)
    export_package_payload = _load_export_package_payload_or_raise(export_package_ref)
    owner_run_id, context_packet_payloads, context_packet_refs, export_refs = _resolve_source_context_packets_or_raise(
        export_package_payload
    )
    if str(dict(package_context_payload.get("source_descriptor") or {}).get("owner_run_id") or "").strip() != owner_run_id:
        raise Layer3ApsContextDossierHandoffError(
            "APS context-dossier handoff requires package-derived context provenance and export-derived context packets to share one owner_run_id"
        )
    try:
        context_dossier_payload = aps_context_dossier_contract.build_context_dossier_payload(
            context_packet_payloads,
            generated_at_utc=_utc_iso(),
        )
        artifact_path = aps_context_dossier.context_dossier_artifact_path(
            owner_run_id=owner_run_id,
            context_dossier_id=str(context_dossier_payload.get("context_dossier_id") or ""),
            reports_dir=settings.connector_reports_dir,
        )
        validated_payload, context_dossier_ref = aps_context_dossier._persist_or_validate_context_dossier(
            artifact_path=artifact_path,
            payload=context_dossier_payload,
        )
    except ValueError as exc:
        raise Layer3ApsContextDossierHandoffError(
            f"APS context-dossier handoff failed ({str(exc) or 'invalid_request'}): {str(exc)}"
        ) from exc
    except aps_context_dossier.ContextDossierError as exc:
        raise Layer3ApsContextDossierHandoffError(
            f"APS context-dossier handoff failed ({exc.code}): {exc.message or str(exc)}"
        ) from exc
    return validated_payload, str(
        validated_payload.get("_context_dossier_ref") or context_dossier_ref
    ), context_packet_refs, export_refs, export_package_ref


def _summary_json(
    *,
    source_row: L3OutputPackage,
    context_dossier_payload: dict[str, Any],
    context_dossier_ref: str,
    context_packet_refs: list[str],
    export_refs: list[str],
    export_package_ref: str,
) -> dict[str, Any]:
    source_packets = [dict(item or {}) for item in list(context_dossier_payload.get("source_packets") or []) if isinstance(item, dict)]
    return {
        "package_kind": PACKAGE_KIND_APS_CONTEXT_DOSSIER_HANDOFF,
        "package_status": source_row.status,
        "source_gate": SOURCE_GATE_D_APS_CONTEXT_DOSSIER_FREEZE,
        "schema_id": APS_CONTEXT_DOSSIER_HANDOFF_SCHEMA_ID,
        "schema_version": APS_CONTEXT_DOSSIER_HANDOFF_SCHEMA_VERSION,
        "aps_target_family": "context_dossier",
        "aps_schema_id": aps_context_dossier_contract.APS_CONTEXT_DOSSIER_SCHEMA_ID,
        "context_dossier_id": str(context_dossier_payload.get("context_dossier_id") or ""),
        "context_dossier_ref": context_dossier_ref,
        "context_dossier_checksum": str(context_dossier_payload.get("context_dossier_checksum") or ""),
        "owner_run_id": str(context_dossier_payload.get("owner_run_id") or ""),
        "source_family": str(context_dossier_payload.get("source_family") or ""),
        "source_packet_count": int(context_dossier_payload.get("source_packet_count") or 0),
        "ordered_source_packets_sha256": str(
            context_dossier_payload.get("ordered_source_packets_sha256") or ""
        ),
        "source_context_packet_ids_json": [
            str(item.get("context_packet_id") or "") for item in source_packets
        ],
        "source_context_packet_refs_json": list(context_packet_refs),
        "source_export_refs_json": list(export_refs),
        "source_export_package_ref": export_package_ref,
        "source_package_kinds_json": [PACKAGE_KIND_APS_CONTEXT_PACKET_PACKAGE_HANDOFF],
        "source_package_refs_json": {
            PACKAGE_KIND_APS_CONTEXT_PACKET_PACKAGE_HANDOFF: str(source_row.payload_ref or ""),
        },
        "compatibility_notes_json": [
            "aps_context_dossier_handoff points at a persisted aps.context_dossier.v1 artifact",
            "aps_context_packet_package_handoff remains the required gating Layer 3 source package for this tranche",
            "dossier inputs stay on the paired export-derived aps.context_packet.v1 branch",
            "package-derived context provenance is used only to recover the persisted export package and its ordered source export refs",
            "context-dossier contract, checksum, and gate semantics are reused without runtime DB writes",
        ],
        "field_map_json": {
            "aps_context_packet_package_handoff.payload_ref": "source_package_refs_json.aps_context_packet_package_handoff",
            "aps_context_packet_package_handoff.payload.source_descriptor.source_ref": "source_export_package_ref",
            "source_export_package_ref": "source_export_refs_json[]",
            "source_export_refs_json[]": "source_context_packet_refs_json[]",
            "source_context_packet_refs_json[]": "source_packets[].context_packet_ref",
        },
        "handoff_status": {
            "status": "aps_context_dossier_emitted",
            "aps_context_packet_package_admitted": True,
            "context_dossier_handoff_admitted": True,
            "context_dossier_persisted": True,
            "runtime_db_writes_performed": False,
            "owner_run_id": str(context_dossier_payload.get("owner_run_id") or ""),
            "source_family": str(context_dossier_payload.get("source_family") or ""),
            "source_packet_count": int(context_dossier_payload.get("source_packet_count") or 0),
            "ordered_source_packets_sha256": str(
                context_dossier_payload.get("ordered_source_packets_sha256") or ""
            ),
            "total_facts": int(context_dossier_payload.get("total_facts") or 0),
            "total_caveats": int(context_dossier_payload.get("total_caveats") or 0),
            "total_constraints": int(context_dossier_payload.get("total_constraints") or 0),
            "total_unresolved_questions": int(
                context_dossier_payload.get("total_unresolved_questions") or 0
            ),
            "source_export_count": len(export_refs),
            "package_context_used_as_provenance_only": True,
        },
    }


def materialize_aps_context_dossier_handoff(
    db: Session,
    *,
    session_id: str,
) -> Layer3ApsContextDossierHandoffResult:
    session = _load_session_or_raise(db, session_id=session_id)
    source_row, reconciliation = _load_source_package_or_raise(db, session_id=session.session_id)
    context_dossier_payload, context_dossier_ref, context_packet_refs, export_refs, export_package_ref = (
        _materialize_context_dossier_or_raise(source_row)
    )
    output_package = L3OutputPackage(
        output_package_id=uuid_str(),
        session_id=session.session_id,
        reconciliation_record_id=reconciliation.reconciliation_record_id,
        package_kind=PACKAGE_KIND_APS_CONTEXT_DOSSIER_HANDOFF,
        status=source_row.status,
        payload_ref=context_dossier_ref,
        payload_hash=hashlib.sha256(Path(context_dossier_ref).read_bytes()).hexdigest(),
        summary_json=_summary_json(
            source_row=source_row,
            context_dossier_payload=context_dossier_payload,
            context_dossier_ref=context_dossier_ref,
            context_packet_refs=context_packet_refs,
            export_refs=export_refs,
            export_package_ref=export_package_ref,
        ),
    )
    db.add(output_package)
    db.flush()
    return Layer3ApsContextDossierHandoffResult(
        output_package=output_package,
        context_dossier_payload=context_dossier_payload,
    )
