from __future__ import annotations

import hashlib
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.models import L3OutputPackage, L3ReconciliationRecord, L3Session, uuid_str
from app.services import nrc_aps_evidence_citation_pack as aps_citation_pack
from app.services import nrc_aps_evidence_citation_pack_contract as aps_citation_contract
from app.services import nrc_aps_evidence_report as aps_report
from app.services import nrc_aps_evidence_report_contract as aps_report_contract
from app.services.layer3_aps_citation_handoff import PACKAGE_KIND_APS_EVIDENCE_CITATION_PACK_HANDOFF
from app.services.layer3_package_entry import (
    PACKAGE_STATUS_COMPLETE,
    PACKAGE_STATUS_COMPLETE_WITH_WARNINGS,
)
from app.services.layer3_session_entry import (
    SESSION_STATUS_COMPLETED,
    SESSION_STATUS_COMPLETED_WITH_WARNINGS,
    SESSION_STATUS_FAILED,
)


PACKAGE_KIND_APS_EVIDENCE_REPORT_HANDOFF = "aps_evidence_report_handoff"
APS_REPORT_HANDOFF_SCHEMA_ID = "layer3.aps_evidence_report_handoff.v1"
APS_REPORT_HANDOFF_SCHEMA_VERSION = 1
SOURCE_GATE_D_APS_REPORT_FREEZE = "11_GATED_APS_REPORT_FREEZE"

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


class Layer3ApsReportHandoffError(ValueError):
    pass


@dataclass(frozen=True)
class Layer3ApsReportHandoffResult:
    output_package: L3OutputPackage
    evidence_report_payload: dict[str, Any]


def _utc_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _require_existing_ref(ref: str | None, *, label: str) -> str:
    normalized = str(ref or "").strip()
    if not normalized:
        raise Layer3ApsReportHandoffError(f"{label} is missing")
    if not Path(normalized).exists():
        raise Layer3ApsReportHandoffError(f"{label} does not exist: {normalized}")
    return normalized


def _load_session_or_raise(db: Session, *, session_id: str) -> L3Session:
    session = db.get(L3Session, session_id)
    if session is None:
        raise Layer3ApsReportHandoffError(f"Layer 3 session '{session_id}' was not found")
    if session.status not in TERMINAL_SESSION_STATUSES or session.completed_at is None:
        raise Layer3ApsReportHandoffError(
            f"Layer 3 session '{session_id}' must be terminal before Gate D APS report handoff"
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
    if PACKAGE_KIND_APS_EVIDENCE_REPORT_HANDOFF in rows_by_kind:
        raise Layer3ApsReportHandoffError(
            f"Layer 3 session '{session_id}' already has an APS evidence-report handoff package"
        )
    source_row = rows_by_kind.get(PACKAGE_KIND_APS_EVIDENCE_CITATION_PACK_HANDOFF)
    if source_row is None:
        raise Layer3ApsReportHandoffError(
            f"Layer 3 session '{session_id}' is missing the APS evidence citation-pack handoff package required for APS report handoff"
        )
    if source_row.status not in ACCEPTED_SOURCE_PACKAGE_STATUSES:
        raise Layer3ApsReportHandoffError(
            f"Layer 3 package '{PACKAGE_KIND_APS_EVIDENCE_CITATION_PACK_HANDOFF}' must be complete before APS report handoff"
        )
    source_summary = dict(source_row.summary_json or {})
    if str(source_summary.get("aps_target_family") or "").strip() != "citation_pack":
        raise Layer3ApsReportHandoffError(
            f"Layer 3 package '{PACKAGE_KIND_APS_EVIDENCE_CITATION_PACK_HANDOFF}' does not point at the citation-pack APS family"
        )
    if (
        str(source_summary.get("aps_schema_id") or "").strip()
        != aps_citation_contract.APS_EVIDENCE_CITATION_PACK_SCHEMA_ID
    ):
        raise Layer3ApsReportHandoffError(
            f"Layer 3 package '{PACKAGE_KIND_APS_EVIDENCE_CITATION_PACK_HANDOFF}' has incompatible APS schema provenance"
        )
    _require_existing_ref(
        source_row.payload_ref,
        label=f"Layer 3 package '{PACKAGE_KIND_APS_EVIDENCE_CITATION_PACK_HANDOFF}' payload ref",
    )
    reconciliation_record_id = str(source_row.reconciliation_record_id or "").strip()
    reconciliation = db.get(L3ReconciliationRecord, reconciliation_record_id)
    if reconciliation is None or reconciliation.session_id != session_id:
        raise Layer3ApsReportHandoffError(
            f"Layer 3 session '{session_id}' is missing reconciliation provenance required for APS report handoff"
        )
    return source_row, reconciliation


def _materialize_evidence_report_or_raise(
    source_row: L3OutputPackage,
) -> tuple[dict[str, Any], str]:
    source_citation_pack_ref = _require_existing_ref(
        source_row.payload_ref,
        label=f"Layer 3 package '{PACKAGE_KIND_APS_EVIDENCE_CITATION_PACK_HANDOFF}' payload ref",
    )
    try:
        source_citation_pack_payload, _source_path = aps_citation_pack.load_persisted_citation_pack_artifact(
            citation_pack_ref=source_citation_pack_ref
        )
        source_citation_pack = aps_report_contract.source_citation_pack_summary_payload(
            source_citation_pack_payload
        )
        evidence_report_id = aps_report_contract.derive_evidence_report_id(
            citation_pack_id=str(source_citation_pack_payload.get("citation_pack_id") or ""),
            citation_pack_checksum=str(source_citation_pack_payload.get("citation_pack_checksum") or ""),
        )
        sections = aps_report_contract.build_sections_from_citation_pack(source_citation_pack_payload)
        evidence_report_payload = {
            "schema_id": aps_report_contract.APS_EVIDENCE_REPORT_SCHEMA_ID,
            "schema_version": aps_report_contract.APS_EVIDENCE_REPORT_SCHEMA_VERSION,
            "generated_at_utc": _utc_iso(),
            "evidence_report_id": evidence_report_id,
            "assembly_contract_id": aps_report_contract.APS_EVIDENCE_REPORT_ASSEMBLY_CONTRACT_ID,
            "sectioning_contract_id": aps_report_contract.APS_EVIDENCE_REPORT_SECTIONING_CONTRACT_ID,
            "source_citation_pack": source_citation_pack,
            "total_sections": len(sections),
            "total_citations": int(source_citation_pack.get("total_citations") or 0),
            "total_groups": int(source_citation_pack.get("total_groups") or 0),
            "sections": sections,
        }
        evidence_report_payload["evidence_report_checksum"] = (
            aps_report_contract.compute_evidence_report_checksum(evidence_report_payload)
        )
        source_bundle = dict(source_citation_pack.get("source_bundle") or {})
        effective_run_id = str(source_bundle.get("run_id") or "").strip()
        if not effective_run_id:
            raise Layer3ApsReportHandoffError(
                "APS evidence-report handoff requires a source citation pack with run_id"
            )
        artifact_path = aps_report.evidence_report_artifact_path(
            run_id=effective_run_id,
            evidence_report_id=evidence_report_id,
            reports_dir=settings.connector_reports_dir,
        )
        validated_payload, evidence_report_ref = aps_report._persist_or_validate_evidence_report(
            artifact_path=artifact_path,
            payload=evidence_report_payload,
        )
        loaded_payload, _persisted_path = aps_report.load_persisted_evidence_report_artifact(
            evidence_report_ref=evidence_report_ref
        )
    except aps_citation_pack.EvidenceCitationPackError as exc:
        raise Layer3ApsReportHandoffError(
            f"APS evidence-report handoff failed ({exc.code}): {exc.message or str(exc)}"
        ) from exc
    except aps_report.EvidenceReportError as exc:
        raise Layer3ApsReportHandoffError(
            f"APS evidence-report handoff failed ({exc.code}): {exc.message or str(exc)}"
        ) from exc
    return loaded_payload or validated_payload, str(
        loaded_payload.get("_evidence_report_ref") or evidence_report_ref
    )


def _summary_json(
    *,
    source_row: L3OutputPackage,
    evidence_report_payload: dict[str, Any],
    evidence_report_ref: str,
) -> dict[str, Any]:
    source_citation_pack = dict(evidence_report_payload.get("source_citation_pack") or {})
    source_bundle = dict(source_citation_pack.get("source_bundle") or {})
    return {
        "package_kind": PACKAGE_KIND_APS_EVIDENCE_REPORT_HANDOFF,
        "package_status": source_row.status,
        "source_gate": SOURCE_GATE_D_APS_REPORT_FREEZE,
        "schema_id": APS_REPORT_HANDOFF_SCHEMA_ID,
        "schema_version": APS_REPORT_HANDOFF_SCHEMA_VERSION,
        "aps_target_family": "evidence_report",
        "aps_schema_id": aps_report_contract.APS_EVIDENCE_REPORT_SCHEMA_ID,
        "evidence_report_id": str(evidence_report_payload.get("evidence_report_id") or ""),
        "evidence_report_ref": evidence_report_ref,
        "evidence_report_checksum": str(
            evidence_report_payload.get("evidence_report_checksum") or ""
        ),
        "source_package_kinds_json": [PACKAGE_KIND_APS_EVIDENCE_CITATION_PACK_HANDOFF],
        "source_package_refs_json": {
            PACKAGE_KIND_APS_EVIDENCE_CITATION_PACK_HANDOFF: str(source_row.payload_ref or ""),
        },
        "compatibility_notes_json": [
            "aps_evidence_report_handoff points at a persisted aps.evidence_report.v1 artifact",
            "aps_evidence_citation_pack_handoff remains the required source package for this tranche",
            "evidence-report schema, checksum, and gate semantics are reused without widening",
            "connector-run runtime refs remain untouched in this Layer 3 handoff path",
        ],
        "field_map_json": {
            "aps_evidence_citation_pack_handoff.payload_ref": "source_citation_pack.citation_pack_ref",
            "source_citation_pack.citation_pack_id": "source_citation_pack.citation_pack_id",
            "source_citation_pack.citation_pack_checksum": "source_citation_pack.citation_pack_checksum",
            "source_citation_pack.source_bundle.run_id": "source_citation_pack.source_bundle.run_id",
            "sections[].section_id": "sections[].section_id",
            "sections[].citations[].citation_id": "sections[].citations[].citation_id",
            "sections[].citations[].highlight_spans": "sections[].citations[].highlight_spans",
        },
        "handoff_status": {
            "status": "aps_evidence_report_emitted",
            "aps_handoff_admitted": True,
            "evidence_report_handoff_admitted": True,
            "evidence_report_persisted": True,
            "runtime_db_writes_performed": False,
            "section_count": int(evidence_report_payload.get("total_sections") or 0),
            "citation_count": int(evidence_report_payload.get("total_citations") or 0),
            "group_count": int(evidence_report_payload.get("total_groups") or 0),
            "source_run_id": str(source_bundle.get("run_id") or ""),
            "source_citation_pack_id": str(source_citation_pack.get("citation_pack_id") or ""),
            "source_citation_pack_checksum": str(
                source_citation_pack.get("citation_pack_checksum") or ""
            ),
            "source_bundle_id": str(source_bundle.get("bundle_id") or ""),
        },
    }


def materialize_aps_report_handoff(
    db: Session,
    *,
    session_id: str,
) -> Layer3ApsReportHandoffResult:
    session = _load_session_or_raise(db, session_id=session_id)
    source_row, reconciliation = _load_source_package_or_raise(db, session_id=session.session_id)
    evidence_report_payload, evidence_report_ref = _materialize_evidence_report_or_raise(source_row)
    output_package = L3OutputPackage(
        output_package_id=uuid_str(),
        session_id=session.session_id,
        reconciliation_record_id=reconciliation.reconciliation_record_id,
        package_kind=PACKAGE_KIND_APS_EVIDENCE_REPORT_HANDOFF,
        status=source_row.status,
        payload_ref=evidence_report_ref,
        payload_hash=hashlib.sha256(Path(evidence_report_ref).read_bytes()).hexdigest(),
        summary_json=_summary_json(
            source_row=source_row,
            evidence_report_payload=evidence_report_payload,
            evidence_report_ref=evidence_report_ref,
        ),
    )
    db.add(output_package)
    db.flush()
    return Layer3ApsReportHandoffResult(
        output_package=output_package,
        evidence_report_payload=evidence_report_payload,
    )
