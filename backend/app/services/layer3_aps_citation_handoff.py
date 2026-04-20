from __future__ import annotations

import hashlib
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.models import L3OutputPackage, L3ReconciliationRecord, L3Session, uuid_str
from app.services import nrc_aps_evidence_bundle as aps_bundle
from app.services import nrc_aps_evidence_bundle_contract as aps_bundle_contract
from app.services import nrc_aps_evidence_citation_pack as aps_citation_pack
from app.services import nrc_aps_evidence_citation_pack_contract as aps_citation_contract
from app.services.layer3_aps_handoff import PACKAGE_KIND_APS_EVIDENCE_BUNDLE_HANDOFF
from app.services.layer3_package_entry import (
    PACKAGE_STATUS_COMPLETE,
    PACKAGE_STATUS_COMPLETE_WITH_WARNINGS,
)
from app.services.layer3_session_entry import (
    SESSION_STATUS_COMPLETED,
    SESSION_STATUS_COMPLETED_WITH_WARNINGS,
    SESSION_STATUS_FAILED,
)


PACKAGE_KIND_APS_EVIDENCE_CITATION_PACK_HANDOFF = "aps_evidence_citation_pack_handoff"
APS_CITATION_HANDOFF_SCHEMA_ID = "layer3.aps_evidence_citation_pack_handoff.v1"
APS_CITATION_HANDOFF_SCHEMA_VERSION = 1
SOURCE_GATE_D_APS_CITATION_FREEZE = "10_GATED_APS_CITATION_FREEZE"

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


class Layer3ApsCitationHandoffError(ValueError):
    pass


@dataclass(frozen=True)
class Layer3ApsCitationHandoffResult:
    output_package: L3OutputPackage
    citation_pack_payload: dict[str, Any]


def _utc_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _require_existing_ref(ref: str | None, *, label: str) -> str:
    normalized = str(ref or "").strip()
    if not normalized:
        raise Layer3ApsCitationHandoffError(f"{label} is missing")
    if not Path(normalized).exists():
        raise Layer3ApsCitationHandoffError(f"{label} does not exist: {normalized}")
    return normalized


def _load_session_or_raise(db: Session, *, session_id: str) -> L3Session:
    session = db.get(L3Session, session_id)
    if session is None:
        raise Layer3ApsCitationHandoffError(f"Layer 3 session '{session_id}' was not found")
    if session.status not in TERMINAL_SESSION_STATUSES or session.completed_at is None:
        raise Layer3ApsCitationHandoffError(
            f"Layer 3 session '{session_id}' must be terminal before Gate D APS citation handoff"
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
    if PACKAGE_KIND_APS_EVIDENCE_CITATION_PACK_HANDOFF in rows_by_kind:
        raise Layer3ApsCitationHandoffError(
            f"Layer 3 session '{session_id}' already has an APS evidence citation-pack handoff package"
        )
    source_row = rows_by_kind.get(PACKAGE_KIND_APS_EVIDENCE_BUNDLE_HANDOFF)
    if source_row is None:
        raise Layer3ApsCitationHandoffError(
            f"Layer 3 session '{session_id}' is missing the APS evidence-bundle handoff package required for APS citation handoff"
        )
    if source_row.status not in ACCEPTED_SOURCE_PACKAGE_STATUSES:
        raise Layer3ApsCitationHandoffError(
            f"Layer 3 package '{PACKAGE_KIND_APS_EVIDENCE_BUNDLE_HANDOFF}' must be complete before APS citation handoff"
        )
    source_summary = dict(source_row.summary_json or {})
    if str(source_summary.get("aps_target_family") or "").strip() != "evidence_bundle":
        raise Layer3ApsCitationHandoffError(
            f"Layer 3 package '{PACKAGE_KIND_APS_EVIDENCE_BUNDLE_HANDOFF}' does not point at the evidence-bundle APS family"
        )
    if (
        str(source_summary.get("aps_schema_id") or "").strip()
        != aps_bundle_contract.APS_EVIDENCE_BUNDLE_SCHEMA_ID
    ):
        raise Layer3ApsCitationHandoffError(
            f"Layer 3 package '{PACKAGE_KIND_APS_EVIDENCE_BUNDLE_HANDOFF}' has incompatible APS schema provenance"
        )
    _require_existing_ref(
        source_row.payload_ref,
        label=f"Layer 3 package '{PACKAGE_KIND_APS_EVIDENCE_BUNDLE_HANDOFF}' payload ref",
    )
    reconciliation_record_id = str(source_row.reconciliation_record_id or "").strip()
    reconciliation = db.get(L3ReconciliationRecord, reconciliation_record_id)
    if reconciliation is None or reconciliation.session_id != session_id:
        raise Layer3ApsCitationHandoffError(
            f"Layer 3 session '{session_id}' is missing reconciliation provenance required for APS citation handoff"
        )
    return source_row, reconciliation


def _materialize_citation_pack_or_raise(source_row: L3OutputPackage) -> tuple[dict[str, Any], str]:
    source_bundle_ref = _require_existing_ref(
        source_row.payload_ref,
        label=f"Layer 3 package '{PACKAGE_KIND_APS_EVIDENCE_BUNDLE_HANDOFF}' payload ref",
    )
    try:
        source_bundle_payload, _source_path = aps_bundle.load_persisted_bundle_artifact(
            bundle_ref=source_bundle_ref
        )
        aps_citation_pack._validate_source_bundle_for_citations(source_bundle_payload)
        source_bundle = aps_citation_contract.source_bundle_summary_payload(source_bundle_payload)
        citation_pack_id = aps_citation_contract.derive_citation_pack_id(
            source_bundle_id=str(source_bundle_payload.get("bundle_id") or ""),
            source_bundle_checksum=str(source_bundle_payload.get("bundle_checksum") or ""),
        )
        citations = aps_citation_contract.build_citations_from_bundle(source_bundle_payload)
        citation_pack_payload = {
            "schema_id": aps_citation_contract.APS_EVIDENCE_CITATION_PACK_SCHEMA_ID,
            "schema_version": aps_citation_contract.APS_EVIDENCE_CITATION_PACK_SCHEMA_VERSION,
            "generated_at_utc": _utc_iso(),
            "citation_pack_id": citation_pack_id,
            "derivation_contract_id": aps_citation_contract.APS_EVIDENCE_CITATION_DERIVATION_CONTRACT_ID,
            "source_bundle": source_bundle,
            "total_citations": len(citations),
            "total_groups": len({str(item.get("group_id") or "") for item in citations}),
            "citations": citations,
        }
        citation_pack_payload["citation_pack_checksum"] = aps_citation_contract.compute_citation_pack_checksum(
            citation_pack_payload
        )
        effective_run_id = str(source_bundle_payload.get("run_id") or "").strip()
        if not effective_run_id:
            raise Layer3ApsCitationHandoffError(
                "APS evidence citation-pack handoff requires a source evidence bundle with run_id"
            )
        artifact_path = aps_citation_pack.citation_pack_artifact_path(
            run_id=effective_run_id,
            citation_pack_id=citation_pack_id,
            reports_dir=settings.connector_reports_dir,
        )
        citation_pack_ref = aps_citation_pack._persist_or_validate_citation_pack(
            artifact_path=artifact_path,
            payload=citation_pack_payload,
        )
        validated_payload, _persisted_path = aps_citation_pack.load_persisted_citation_pack_artifact(
            citation_pack_ref=citation_pack_ref
        )
    except aps_bundle.EvidenceBundleError as exc:
        raise Layer3ApsCitationHandoffError(
            f"APS evidence citation-pack handoff failed ({exc.code}): {exc.message or str(exc)}"
        ) from exc
    except aps_citation_pack.EvidenceCitationPackError as exc:
        raise Layer3ApsCitationHandoffError(
            f"APS evidence citation-pack handoff failed ({exc.code}): {exc.message or str(exc)}"
        ) from exc
    return validated_payload, str(validated_payload.get("_citation_pack_ref") or citation_pack_ref)


def _summary_json(
    *,
    source_row: L3OutputPackage,
    citation_pack_payload: dict[str, Any],
    citation_pack_ref: str,
) -> dict[str, Any]:
    source_bundle = dict(citation_pack_payload.get("source_bundle") or {})
    return {
        "package_kind": PACKAGE_KIND_APS_EVIDENCE_CITATION_PACK_HANDOFF,
        "package_status": source_row.status,
        "source_gate": SOURCE_GATE_D_APS_CITATION_FREEZE,
        "schema_id": APS_CITATION_HANDOFF_SCHEMA_ID,
        "schema_version": APS_CITATION_HANDOFF_SCHEMA_VERSION,
        "aps_target_family": "citation_pack",
        "aps_schema_id": aps_citation_contract.APS_EVIDENCE_CITATION_PACK_SCHEMA_ID,
        "citation_pack_id": str(citation_pack_payload.get("citation_pack_id") or ""),
        "citation_pack_ref": citation_pack_ref,
        "citation_pack_checksum": str(citation_pack_payload.get("citation_pack_checksum") or ""),
        "source_package_kinds_json": [PACKAGE_KIND_APS_EVIDENCE_BUNDLE_HANDOFF],
        "source_package_refs_json": {
            PACKAGE_KIND_APS_EVIDENCE_BUNDLE_HANDOFF: str(source_row.payload_ref or ""),
        },
        "compatibility_notes_json": [
            "aps_evidence_citation_pack_handoff points at a persisted aps.evidence_citation_pack.v2 artifact",
            "aps_evidence_bundle_handoff remains the required source package for this tranche",
            "citation-pack contract, checksum, and gate semantics are reused without widening",
            "connector-run runtime refs remain untouched in this Layer 3 handoff path",
        ],
        "field_map_json": {
            "aps_evidence_bundle_handoff.payload_ref": "source_bundle.bundle_ref",
            "source_bundle.bundle_id": "source_bundle.bundle_id",
            "source_bundle.bundle_checksum": "source_bundle.bundle_checksum",
            "source_bundle.run_id": "source_bundle.run_id",
            "citations[].citation_id": "citations[].citation_id",
            "citations[].chunk_id": "citations[].chunk_id",
            "citations[].highlight_spans": "citations[].highlight_spans",
        },
        "handoff_status": {
            "status": "aps_evidence_citation_pack_emitted",
            "aps_handoff_admitted": True,
            "citation_pack_handoff_admitted": True,
            "citation_pack_persisted": True,
            "runtime_db_writes_performed": False,
            "citation_count": int(citation_pack_payload.get("total_citations") or 0),
            "citation_group_count": int(citation_pack_payload.get("total_groups") or 0),
            "source_run_id": str(source_bundle.get("run_id") or ""),
            "source_bundle_id": str(source_bundle.get("bundle_id") or ""),
            "source_bundle_checksum": str(source_bundle.get("bundle_checksum") or ""),
        },
    }


def materialize_aps_citation_handoff(
    db: Session,
    *,
    session_id: str,
) -> Layer3ApsCitationHandoffResult:
    session = _load_session_or_raise(db, session_id=session_id)
    source_row, reconciliation = _load_source_package_or_raise(db, session_id=session.session_id)
    citation_pack_payload, citation_pack_ref = _materialize_citation_pack_or_raise(source_row)
    output_package = L3OutputPackage(
        output_package_id=uuid_str(),
        session_id=session.session_id,
        reconciliation_record_id=reconciliation.reconciliation_record_id,
        package_kind=PACKAGE_KIND_APS_EVIDENCE_CITATION_PACK_HANDOFF,
        status=source_row.status,
        payload_ref=citation_pack_ref,
        payload_hash=hashlib.sha256(Path(citation_pack_ref).read_bytes()).hexdigest(),
        summary_json=_summary_json(
            source_row=source_row,
            citation_pack_payload=citation_pack_payload,
            citation_pack_ref=citation_pack_ref,
        ),
    )
    db.add(output_package)
    db.flush()
    return Layer3ApsCitationHandoffResult(
        output_package=output_package,
        citation_pack_payload=citation_pack_payload,
    )
