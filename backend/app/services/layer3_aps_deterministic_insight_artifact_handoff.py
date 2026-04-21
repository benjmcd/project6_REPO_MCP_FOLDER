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
from app.services import nrc_aps_context_packet_contract as aps_context_packet_contract
from app.services import nrc_aps_deterministic_insight_artifact as aps_insight_artifact
from app.services import nrc_aps_deterministic_insight_artifact_contract as aps_insight_contract
from app.services.layer3_aps_context_dossier_handoff import PACKAGE_KIND_APS_CONTEXT_DOSSIER_HANDOFF
from app.services.layer3_package_entry import (
    PACKAGE_STATUS_COMPLETE,
    PACKAGE_STATUS_COMPLETE_WITH_WARNINGS,
)
from app.services.layer3_session_entry import (
    SESSION_STATUS_COMPLETED,
    SESSION_STATUS_COMPLETED_WITH_WARNINGS,
    SESSION_STATUS_FAILED,
)


PACKAGE_KIND_APS_DETERMINISTIC_INSIGHT_ARTIFACT_HANDOFF = "aps_deterministic_insight_artifact_handoff"
APS_DETERMINISTIC_INSIGHT_ARTIFACT_HANDOFF_SCHEMA_ID = "layer3.aps_deterministic_insight_artifact_handoff.v1"
APS_DETERMINISTIC_INSIGHT_ARTIFACT_HANDOFF_SCHEMA_VERSION = 1
SOURCE_GATE_D_APS_DETERMINISTIC_INSIGHT_FREEZE = "18_GATED_APS_DETERMINISTIC_INSIGHT_FREEZE"

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


class Layer3ApsDeterministicInsightArtifactHandoffError(ValueError):
    pass


@dataclass(frozen=True)
class Layer3ApsDeterministicInsightArtifactHandoffResult:
    output_package: L3OutputPackage
    deterministic_insight_artifact_payload: dict[str, Any]


def _utc_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _require_existing_ref(ref: str | None, *, label: str) -> str:
    normalized = str(ref or "").strip()
    if not normalized:
        raise Layer3ApsDeterministicInsightArtifactHandoffError(f"{label} is missing")
    if not Path(normalized).exists():
        raise Layer3ApsDeterministicInsightArtifactHandoffError(f"{label} does not exist: {normalized}")
    return normalized


def _load_session_or_raise(db: Session, *, session_id: str) -> L3Session:
    session = db.get(L3Session, session_id)
    if session is None:
        raise Layer3ApsDeterministicInsightArtifactHandoffError(
            f"Layer 3 session '{session_id}' was not found"
        )
    if session.status not in TERMINAL_SESSION_STATUSES or session.completed_at is None:
        raise Layer3ApsDeterministicInsightArtifactHandoffError(
            f"Layer 3 session '{session_id}' must be terminal before Gate D APS deterministic-insight handoff"
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
    if PACKAGE_KIND_APS_DETERMINISTIC_INSIGHT_ARTIFACT_HANDOFF in rows_by_kind:
        raise Layer3ApsDeterministicInsightArtifactHandoffError(
            f"Layer 3 session '{session_id}' already has an APS deterministic-insight handoff package"
        )
    source_row = rows_by_kind.get(PACKAGE_KIND_APS_CONTEXT_DOSSIER_HANDOFF)
    if source_row is None:
        raise Layer3ApsDeterministicInsightArtifactHandoffError(
            f"Layer 3 session '{session_id}' is missing the APS context-dossier handoff package required for APS deterministic-insight handoff"
        )
    if source_row.status not in ACCEPTED_SOURCE_PACKAGE_STATUSES:
        raise Layer3ApsDeterministicInsightArtifactHandoffError(
            f"Layer 3 package '{PACKAGE_KIND_APS_CONTEXT_DOSSIER_HANDOFF}' must be complete before APS deterministic-insight handoff"
        )
    source_summary = dict(source_row.summary_json or {})
    if str(source_summary.get("aps_target_family") or "").strip() != "context_dossier":
        raise Layer3ApsDeterministicInsightArtifactHandoffError(
            f"Layer 3 package '{PACKAGE_KIND_APS_CONTEXT_DOSSIER_HANDOFF}' does not point at the APS context-dossier family"
        )
    if (
        str(source_summary.get("aps_schema_id") or "").strip()
        != aps_context_dossier_contract.APS_CONTEXT_DOSSIER_SCHEMA_ID
    ):
        raise Layer3ApsDeterministicInsightArtifactHandoffError(
            f"Layer 3 package '{PACKAGE_KIND_APS_CONTEXT_DOSSIER_HANDOFF}' has incompatible APS schema provenance"
        )
    _require_existing_ref(
        source_row.payload_ref,
        label=f"Layer 3 package '{PACKAGE_KIND_APS_CONTEXT_DOSSIER_HANDOFF}' payload ref",
    )
    reconciliation_record_id = str(source_row.reconciliation_record_id or "").strip()
    reconciliation = db.get(L3ReconciliationRecord, reconciliation_record_id)
    if reconciliation is None or reconciliation.session_id != session_id:
        raise Layer3ApsDeterministicInsightArtifactHandoffError(
            f"Layer 3 session '{session_id}' is missing reconciliation provenance required for APS deterministic-insight handoff"
        )
    return source_row, reconciliation


def _load_context_dossier_payload_or_raise(source_row: L3OutputPackage) -> tuple[dict[str, Any], str]:
    context_dossier_ref = _require_existing_ref(
        source_row.payload_ref,
        label=f"Layer 3 package '{PACKAGE_KIND_APS_CONTEXT_DOSSIER_HANDOFF}' payload ref",
    )
    try:
        context_dossier_payload, _context_dossier_path = aps_context_dossier.load_persisted_context_dossier_artifact(
            context_dossier_ref=context_dossier_ref
        )
    except aps_context_dossier.ContextDossierError as exc:
        raise Layer3ApsDeterministicInsightArtifactHandoffError(
            f"APS deterministic-insight handoff failed ({exc.code}): {exc.message or str(exc)}"
        ) from exc
    if (
        str(context_dossier_payload.get("source_family") or "").strip()
        != aps_context_packet_contract.APS_CONTEXT_PACKET_SOURCE_FAMILY_EXPORT
    ):
        raise Layer3ApsDeterministicInsightArtifactHandoffError(
            "APS deterministic-insight handoff requires the current context-dossier handoff package to remain on the paired export-derived context-packet branch"
        )
    owner_run_id = str(context_dossier_payload.get("owner_run_id") or "").strip()
    if not owner_run_id:
        raise Layer3ApsDeterministicInsightArtifactHandoffError(
            "APS deterministic-insight handoff requires a persisted context dossier with owner_run_id"
        )
    return context_dossier_payload, context_dossier_ref


def _materialize_deterministic_insight_artifact_or_raise(
    source_row: L3OutputPackage,
) -> tuple[dict[str, Any], str]:
    source_context_dossier_payload, _context_dossier_ref = _load_context_dossier_payload_or_raise(source_row)
    owner_run_id = str(source_context_dossier_payload.get("owner_run_id") or "").strip()
    try:
        deterministic_insight_payload = aps_insight_contract.build_deterministic_insight_artifact_payload(
            source_context_dossier_payload,
            generated_at_utc=_utc_iso(),
        )
        artifact_path = aps_insight_artifact.deterministic_insight_artifact_path(
            owner_run_id=owner_run_id,
            deterministic_insight_artifact_id=str(
                deterministic_insight_payload.get("deterministic_insight_artifact_id") or ""
            ),
            reports_dir=settings.connector_reports_dir,
        )
        validated_payload, deterministic_insight_ref = (
            aps_insight_artifact._persist_or_validate_deterministic_insight_artifact(
                artifact_path=artifact_path,
                payload=deterministic_insight_payload,
            )
        )
    except ValueError as exc:
        raise Layer3ApsDeterministicInsightArtifactHandoffError(
            f"APS deterministic-insight handoff failed ({str(exc) or 'invalid_request'}): {str(exc)}"
        ) from exc
    except aps_insight_artifact.DeterministicInsightArtifactError as exc:
        raise Layer3ApsDeterministicInsightArtifactHandoffError(
            f"APS deterministic-insight handoff failed ({exc.code}): {exc.message or str(exc)}"
        ) from exc
    return validated_payload, str(
        validated_payload.get("_deterministic_insight_artifact_ref") or deterministic_insight_ref
    )


def _summary_json(
    *,
    source_row: L3OutputPackage,
    deterministic_insight_payload: dict[str, Any],
    deterministic_insight_ref: str,
) -> dict[str, Any]:
    source_context_dossier = dict(deterministic_insight_payload.get("source_context_dossier") or {})
    source_packets = [
        dict(item or {})
        for item in list(source_context_dossier.get("source_packets") or [])
        if isinstance(item, dict)
    ]
    finding_counts = {
        severity: int(dict(deterministic_insight_payload.get("finding_counts") or {}).get(severity, 0) or 0)
        for severity in aps_insight_contract.APS_FINDING_SEVERITIES
    }
    return {
        "package_kind": PACKAGE_KIND_APS_DETERMINISTIC_INSIGHT_ARTIFACT_HANDOFF,
        "package_status": source_row.status,
        "source_gate": SOURCE_GATE_D_APS_DETERMINISTIC_INSIGHT_FREEZE,
        "schema_id": APS_DETERMINISTIC_INSIGHT_ARTIFACT_HANDOFF_SCHEMA_ID,
        "schema_version": APS_DETERMINISTIC_INSIGHT_ARTIFACT_HANDOFF_SCHEMA_VERSION,
        "aps_target_family": "deterministic_insight_artifact",
        "aps_schema_id": aps_insight_contract.APS_DETERMINISTIC_INSIGHT_ARTIFACT_SCHEMA_ID,
        "deterministic_insight_artifact_id": str(
            deterministic_insight_payload.get("deterministic_insight_artifact_id") or ""
        ),
        "deterministic_insight_artifact_ref": deterministic_insight_ref,
        "deterministic_insight_artifact_checksum": str(
            deterministic_insight_payload.get("deterministic_insight_artifact_checksum") or ""
        ),
        "ruleset_contract_id": str(deterministic_insight_payload.get("ruleset_contract_id") or ""),
        "ruleset_id": str(deterministic_insight_payload.get("ruleset_id") or ""),
        "ruleset_version": int(deterministic_insight_payload.get("ruleset_version") or 0),
        "insight_mode": str(deterministic_insight_payload.get("insight_mode") or ""),
        "owner_run_id": str(source_context_dossier.get("owner_run_id") or ""),
        "source_context_dossier_id": str(source_context_dossier.get("context_dossier_id") or ""),
        "source_context_dossier_ref": str(source_context_dossier.get("context_dossier_ref") or ""),
        "source_context_dossier_checksum": str(source_context_dossier.get("context_dossier_checksum") or ""),
        "source_dossier_source_family": str(source_context_dossier.get("source_family") or ""),
        "source_packet_count": int(source_context_dossier.get("source_packet_count") or 0),
        "ordered_source_packets_sha256": str(source_context_dossier.get("ordered_source_packets_sha256") or ""),
        "source_context_packet_ids_json": [
            str(item.get("context_packet_id") or "") for item in source_packets
        ],
        "source_package_kinds_json": [PACKAGE_KIND_APS_CONTEXT_DOSSIER_HANDOFF],
        "source_package_refs_json": {
            PACKAGE_KIND_APS_CONTEXT_DOSSIER_HANDOFF: str(source_row.payload_ref or ""),
        },
        "total_findings": int(deterministic_insight_payload.get("total_findings") or 0),
        "finding_counts": finding_counts,
        "compatibility_notes_json": [
            "aps_deterministic_insight_artifact_handoff points at a persisted aps.deterministic_insight_artifact.v1 artifact",
            "aps_context_dossier_handoff remains the required gating Layer 3 source package for this tranche",
            "deterministic insight continues to derive from the paired export-derived context-packet dossier branch",
            "deterministic insight contract, checksum, and gate semantics are reused without runtime DB writes",
            "connector-run runtime refs and summaries remain untouched in this Layer 3 handoff path",
        ],
        "field_map_json": {
            "aps_context_dossier_handoff.payload_ref": "source_package_refs_json.aps_context_dossier_handoff",
            "source_context_dossier.context_dossier_ref": "source_context_dossier_ref",
            "source_context_dossier.source_packets[].context_packet_id": "source_context_packet_ids_json[]",
            "findings[].rule_id": "findings[].rule_id",
            "finding_counts": "finding_counts",
        },
        "handoff_status": {
            "status": "aps_deterministic_insight_artifact_emitted",
            "aps_context_dossier_admitted": True,
            "deterministic_insight_artifact_handoff_admitted": True,
            "deterministic_insight_artifact_persisted": True,
            "runtime_db_writes_performed": False,
            "owner_run_id": str(source_context_dossier.get("owner_run_id") or ""),
            "source_context_dossier_id": str(source_context_dossier.get("context_dossier_id") or ""),
            "source_dossier_source_family": str(source_context_dossier.get("source_family") or ""),
            "source_packet_count": int(source_context_dossier.get("source_packet_count") or 0),
            "ordered_source_packets_sha256": str(
                source_context_dossier.get("ordered_source_packets_sha256") or ""
            ),
            "total_findings": int(deterministic_insight_payload.get("total_findings") or 0),
            "finding_counts": finding_counts,
        },
    }


def materialize_aps_deterministic_insight_artifact_handoff(
    db: Session,
    *,
    session_id: str,
) -> Layer3ApsDeterministicInsightArtifactHandoffResult:
    session = _load_session_or_raise(db, session_id=session_id)
    source_row, reconciliation = _load_source_package_or_raise(db, session_id=session.session_id)
    deterministic_insight_payload, deterministic_insight_ref = (
        _materialize_deterministic_insight_artifact_or_raise(source_row)
    )
    output_package = L3OutputPackage(
        output_package_id=uuid_str(),
        session_id=session.session_id,
        reconciliation_record_id=reconciliation.reconciliation_record_id,
        package_kind=PACKAGE_KIND_APS_DETERMINISTIC_INSIGHT_ARTIFACT_HANDOFF,
        status=source_row.status,
        payload_ref=deterministic_insight_ref,
        payload_hash=hashlib.sha256(Path(deterministic_insight_ref).read_bytes()).hexdigest(),
        summary_json=_summary_json(
            source_row=source_row,
            deterministic_insight_payload=deterministic_insight_payload,
            deterministic_insight_ref=deterministic_insight_ref,
        ),
    )
    db.add(output_package)
    db.flush()
    return Layer3ApsDeterministicInsightArtifactHandoffResult(
        output_package=output_package,
        deterministic_insight_artifact_payload=deterministic_insight_payload,
    )
