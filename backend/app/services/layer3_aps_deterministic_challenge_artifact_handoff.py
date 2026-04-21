from __future__ import annotations

import hashlib
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.models import L3OutputPackage, L3ReconciliationRecord, L3Session, uuid_str
from app.services import nrc_aps_deterministic_challenge_artifact as aps_challenge_artifact
from app.services import nrc_aps_deterministic_challenge_artifact_contract as aps_challenge_contract
from app.services import nrc_aps_deterministic_insight_artifact as aps_insight_artifact
from app.services import nrc_aps_deterministic_insight_artifact_contract as aps_insight_contract
from app.services.layer3_aps_deterministic_insight_artifact_handoff import (
    PACKAGE_KIND_APS_DETERMINISTIC_INSIGHT_ARTIFACT_HANDOFF,
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


PACKAGE_KIND_APS_DETERMINISTIC_CHALLENGE_ARTIFACT_HANDOFF = (
    "aps_deterministic_challenge_artifact_handoff"
)
APS_DETERMINISTIC_CHALLENGE_ARTIFACT_HANDOFF_SCHEMA_ID = (
    "layer3.aps_deterministic_challenge_artifact_handoff.v1"
)
APS_DETERMINISTIC_CHALLENGE_ARTIFACT_HANDOFF_SCHEMA_VERSION = 1
SOURCE_GATE_D_APS_DETERMINISTIC_CHALLENGE_FREEZE = "19_GATED_APS_DETERMINISTIC_CHALLENGE_FREEZE"

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


class Layer3ApsDeterministicChallengeArtifactHandoffError(ValueError):
    pass


@dataclass(frozen=True)
class Layer3ApsDeterministicChallengeArtifactHandoffResult:
    output_package: L3OutputPackage
    deterministic_challenge_artifact_payload: dict[str, Any]


def _utc_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _require_existing_ref(ref: str | None, *, label: str) -> str:
    normalized = str(ref or "").strip()
    if not normalized:
        raise Layer3ApsDeterministicChallengeArtifactHandoffError(f"{label} is missing")
    if not Path(normalized).exists():
        raise Layer3ApsDeterministicChallengeArtifactHandoffError(
            f"{label} does not exist: {normalized}"
        )
    return normalized


def _load_session_or_raise(db: Session, *, session_id: str) -> L3Session:
    session = db.get(L3Session, session_id)
    if session is None:
        raise Layer3ApsDeterministicChallengeArtifactHandoffError(
            f"Layer 3 session '{session_id}' was not found"
        )
    if session.status not in TERMINAL_SESSION_STATUSES or session.completed_at is None:
        raise Layer3ApsDeterministicChallengeArtifactHandoffError(
            f"Layer 3 session '{session_id}' must be terminal before Gate D APS deterministic-challenge handoff"
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
    if PACKAGE_KIND_APS_DETERMINISTIC_CHALLENGE_ARTIFACT_HANDOFF in rows_by_kind:
        raise Layer3ApsDeterministicChallengeArtifactHandoffError(
            f"Layer 3 session '{session_id}' already has an APS deterministic-challenge handoff package"
        )
    source_row = rows_by_kind.get(PACKAGE_KIND_APS_DETERMINISTIC_INSIGHT_ARTIFACT_HANDOFF)
    if source_row is None:
        raise Layer3ApsDeterministicChallengeArtifactHandoffError(
            f"Layer 3 session '{session_id}' is missing the APS deterministic-insight handoff package required for APS deterministic-challenge handoff"
        )
    if source_row.status not in ACCEPTED_SOURCE_PACKAGE_STATUSES:
        raise Layer3ApsDeterministicChallengeArtifactHandoffError(
            f"Layer 3 package '{PACKAGE_KIND_APS_DETERMINISTIC_INSIGHT_ARTIFACT_HANDOFF}' must be complete before APS deterministic-challenge handoff"
        )
    source_summary = dict(source_row.summary_json or {})
    if str(source_summary.get("aps_target_family") or "").strip() != "deterministic_insight_artifact":
        raise Layer3ApsDeterministicChallengeArtifactHandoffError(
            f"Layer 3 package '{PACKAGE_KIND_APS_DETERMINISTIC_INSIGHT_ARTIFACT_HANDOFF}' does not point at the APS deterministic-insight family"
        )
    if (
        str(source_summary.get("aps_schema_id") or "").strip()
        != aps_insight_contract.APS_DETERMINISTIC_INSIGHT_ARTIFACT_SCHEMA_ID
    ):
        raise Layer3ApsDeterministicChallengeArtifactHandoffError(
            f"Layer 3 package '{PACKAGE_KIND_APS_DETERMINISTIC_INSIGHT_ARTIFACT_HANDOFF}' has incompatible APS schema provenance"
        )
    _require_existing_ref(
        source_row.payload_ref,
        label=f"Layer 3 package '{PACKAGE_KIND_APS_DETERMINISTIC_INSIGHT_ARTIFACT_HANDOFF}' payload ref",
    )
    reconciliation_record_id = str(source_row.reconciliation_record_id or "").strip()
    reconciliation = db.get(L3ReconciliationRecord, reconciliation_record_id)
    if reconciliation is None or reconciliation.session_id != session_id:
        raise Layer3ApsDeterministicChallengeArtifactHandoffError(
            f"Layer 3 session '{session_id}' is missing reconciliation provenance required for APS deterministic-challenge handoff"
        )
    return source_row, reconciliation


def _load_deterministic_insight_payload_or_raise(
    source_row: L3OutputPackage,
) -> tuple[dict[str, Any], str]:
    deterministic_insight_ref = _require_existing_ref(
        source_row.payload_ref,
        label=f"Layer 3 package '{PACKAGE_KIND_APS_DETERMINISTIC_INSIGHT_ARTIFACT_HANDOFF}' payload ref",
    )
    try:
        deterministic_insight_payload, _insight_path = (
            aps_insight_artifact.load_persisted_deterministic_insight_artifact(
                deterministic_insight_artifact_ref=deterministic_insight_ref
            )
        )
    except aps_insight_artifact.DeterministicInsightArtifactError as exc:
        raise Layer3ApsDeterministicChallengeArtifactHandoffError(
            f"APS deterministic-challenge handoff failed ({exc.code}): {exc.message or str(exc)}"
        ) from exc
    owner_run_id = str(
        dict(deterministic_insight_payload.get("source_context_dossier") or {}).get("owner_run_id") or ""
    ).strip()
    if not owner_run_id:
        raise Layer3ApsDeterministicChallengeArtifactHandoffError(
            "APS deterministic-challenge handoff requires a persisted deterministic insight artifact with owner_run_id"
        )
    return deterministic_insight_payload, deterministic_insight_ref


def _materialize_deterministic_challenge_artifact_or_raise(
    source_row: L3OutputPackage,
) -> tuple[dict[str, Any], str]:
    deterministic_insight_payload, _deterministic_insight_ref = (
        _load_deterministic_insight_payload_or_raise(source_row)
    )
    source_summary = aps_challenge_contract.source_deterministic_insight_artifact_summary_payload(
        deterministic_insight_payload
    )
    owner_run_id = str(source_summary.get("owner_run_id") or "").strip()
    try:
        deterministic_challenge_payload = (
            aps_challenge_contract.build_deterministic_challenge_artifact_payload(
                deterministic_insight_payload,
                generated_at_utc=_utc_iso(),
            )
        )
        artifact_path = aps_challenge_artifact.deterministic_challenge_artifact_path(
            owner_run_id=owner_run_id,
            deterministic_challenge_artifact_id=str(
                deterministic_challenge_payload.get("deterministic_challenge_artifact_id") or ""
            ),
            reports_dir=settings.connector_reports_dir,
        )
        validated_payload, deterministic_challenge_ref = (
            aps_challenge_artifact._persist_or_validate_deterministic_challenge_artifact(
                artifact_path=artifact_path,
                payload=deterministic_challenge_payload,
            )
        )
    except ValueError as exc:
        raise Layer3ApsDeterministicChallengeArtifactHandoffError(
            f"APS deterministic-challenge handoff failed ({str(exc) or 'invalid_request'}): {str(exc)}"
        ) from exc
    except aps_challenge_artifact.DeterministicChallengeArtifactError as exc:
        raise Layer3ApsDeterministicChallengeArtifactHandoffError(
            f"APS deterministic-challenge handoff failed ({exc.code}): {exc.message or str(exc)}"
        ) from exc
    return validated_payload, str(
        validated_payload.get("_deterministic_challenge_artifact_ref") or deterministic_challenge_ref
    )


def _summary_json(
    *,
    source_row: L3OutputPackage,
    deterministic_challenge_payload: dict[str, Any],
    deterministic_challenge_ref: str,
) -> dict[str, Any]:
    source_insight = dict(deterministic_challenge_payload.get("source_deterministic_insight_artifact") or {})
    challenge_counts = {
        severity: int(
            dict(deterministic_challenge_payload.get("challenge_counts") or {}).get(severity, 0) or 0
        )
        for severity in aps_challenge_contract.APS_CHALLENGE_SEVERITIES
    }
    disposition_counts = {
        disposition: int(
            dict(deterministic_challenge_payload.get("disposition_counts") or {}).get(disposition, 0) or 0
        )
        for disposition in aps_challenge_contract.APS_CHALLENGE_DISPOSITIONS
    }
    return {
        "package_kind": PACKAGE_KIND_APS_DETERMINISTIC_CHALLENGE_ARTIFACT_HANDOFF,
        "package_status": source_row.status,
        "source_gate": SOURCE_GATE_D_APS_DETERMINISTIC_CHALLENGE_FREEZE,
        "schema_id": APS_DETERMINISTIC_CHALLENGE_ARTIFACT_HANDOFF_SCHEMA_ID,
        "schema_version": APS_DETERMINISTIC_CHALLENGE_ARTIFACT_HANDOFF_SCHEMA_VERSION,
        "aps_target_family": "deterministic_challenge_artifact",
        "aps_schema_id": aps_challenge_contract.APS_DETERMINISTIC_CHALLENGE_ARTIFACT_SCHEMA_ID,
        "deterministic_challenge_artifact_id": str(
            deterministic_challenge_payload.get("deterministic_challenge_artifact_id") or ""
        ),
        "deterministic_challenge_artifact_ref": deterministic_challenge_ref,
        "deterministic_challenge_artifact_checksum": str(
            deterministic_challenge_payload.get("deterministic_challenge_artifact_checksum") or ""
        ),
        "ruleset_contract_id": str(deterministic_challenge_payload.get("ruleset_contract_id") or ""),
        "ruleset_id": str(deterministic_challenge_payload.get("ruleset_id") or ""),
        "ruleset_version": int(deterministic_challenge_payload.get("ruleset_version") or 0),
        "challenge_mode": str(deterministic_challenge_payload.get("challenge_mode") or ""),
        "owner_run_id": str(source_insight.get("owner_run_id") or ""),
        "source_deterministic_insight_artifact_id": str(
            source_insight.get("deterministic_insight_artifact_id") or ""
        ),
        "source_deterministic_insight_artifact_ref": str(
            source_insight.get("deterministic_insight_artifact_ref") or ""
        ),
        "source_deterministic_insight_artifact_checksum": str(
            source_insight.get("deterministic_insight_artifact_checksum") or ""
        ),
        "source_context_dossier_id": str(source_insight.get("source_context_dossier_id") or ""),
        "source_context_dossier_ref": str(source_insight.get("source_context_dossier_ref") or ""),
        "source_context_dossier_checksum": str(
            source_insight.get("source_context_dossier_checksum") or ""
        ),
        "total_findings": int(source_insight.get("total_findings") or 0),
        "source_finding_counts": {
            severity: int(dict(source_insight.get("finding_counts") or {}).get(severity, 0) or 0)
            for severity in aps_insight_contract.APS_FINDING_SEVERITIES
        },
        "total_challenges": int(deterministic_challenge_payload.get("total_challenges") or 0),
        "challenge_counts": challenge_counts,
        "disposition_counts": disposition_counts,
        "source_package_kinds_json": [PACKAGE_KIND_APS_DETERMINISTIC_INSIGHT_ARTIFACT_HANDOFF],
        "source_package_refs_json": {
            PACKAGE_KIND_APS_DETERMINISTIC_INSIGHT_ARTIFACT_HANDOFF: str(source_row.payload_ref or ""),
        },
        "compatibility_notes_json": [
            "aps_deterministic_challenge_artifact_handoff points at a persisted aps.deterministic_challenge_artifact.v1 artifact",
            "aps_deterministic_insight_artifact_handoff remains the required gating Layer 3 source package for this tranche",
            "deterministic challenge continues to derive from one persisted deterministic insight artifact on the landed context-dossier branch",
            "deterministic challenge contract, checksum, and gate semantics are reused without runtime DB writes",
            "connector-run runtime refs and summaries remain untouched in this Layer 3 handoff path",
        ],
        "field_map_json": {
            "aps_deterministic_insight_artifact_handoff.payload_ref": "source_package_refs_json.aps_deterministic_insight_artifact_handoff",
            "source_deterministic_insight_artifact.deterministic_insight_artifact_ref": "source_deterministic_insight_artifact_ref",
            "source_deterministic_insight_artifact.source_context_dossier_ref": "source_context_dossier_ref",
            "challenges[].check_id": "challenges[].check_id",
            "challenge_counts": "challenge_counts",
            "disposition_counts": "disposition_counts",
        },
        "handoff_status": {
            "status": "aps_deterministic_challenge_artifact_emitted",
            "aps_deterministic_insight_artifact_admitted": True,
            "deterministic_challenge_artifact_handoff_admitted": True,
            "deterministic_challenge_artifact_persisted": True,
            "runtime_db_writes_performed": False,
            "owner_run_id": str(source_insight.get("owner_run_id") or ""),
            "source_deterministic_insight_artifact_id": str(
                source_insight.get("deterministic_insight_artifact_id") or ""
            ),
            "source_context_dossier_id": str(source_insight.get("source_context_dossier_id") or ""),
            "total_findings": int(source_insight.get("total_findings") or 0),
            "total_challenges": int(deterministic_challenge_payload.get("total_challenges") or 0),
            "challenge_counts": challenge_counts,
            "disposition_counts": disposition_counts,
        },
    }


def materialize_aps_deterministic_challenge_artifact_handoff(
    db: Session,
    *,
    session_id: str,
) -> Layer3ApsDeterministicChallengeArtifactHandoffResult:
    session = _load_session_or_raise(db, session_id=session_id)
    source_row, reconciliation = _load_source_package_or_raise(db, session_id=session.session_id)
    deterministic_challenge_payload, deterministic_challenge_ref = (
        _materialize_deterministic_challenge_artifact_or_raise(source_row)
    )
    output_package = L3OutputPackage(
        output_package_id=uuid_str(),
        session_id=session.session_id,
        reconciliation_record_id=reconciliation.reconciliation_record_id,
        package_kind=PACKAGE_KIND_APS_DETERMINISTIC_CHALLENGE_ARTIFACT_HANDOFF,
        status=source_row.status,
        payload_ref=deterministic_challenge_ref,
        payload_hash=hashlib.sha256(Path(deterministic_challenge_ref).read_bytes()).hexdigest(),
        summary_json=_summary_json(
            source_row=source_row,
            deterministic_challenge_payload=deterministic_challenge_payload,
            deterministic_challenge_ref=deterministic_challenge_ref,
        ),
    )
    db.add(output_package)
    db.flush()
    return Layer3ApsDeterministicChallengeArtifactHandoffResult(
        output_package=output_package,
        deterministic_challenge_artifact_payload=deterministic_challenge_payload,
    )
