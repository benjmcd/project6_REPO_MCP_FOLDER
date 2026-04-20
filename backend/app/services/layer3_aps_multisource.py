from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.models import L3MaterialSnapshot, L3OutputPackage, L3ReconciliationRecord, L3Session, uuid_str
from app.services.layer3_package_entry import (
    PACKAGE_KIND_CANONICAL_INTERNAL,
    PACKAGE_STATUS_COMPLETE,
    PACKAGE_STATUS_COMPLETE_WITH_WARNINGS,
)
from app.services.layer3_session_entry import (
    SESSION_STATUS_COMPLETED,
    SESSION_STATUS_COMPLETED_WITH_WARNINGS,
    SESSION_STATUS_FAILED,
)


PACKAGE_KIND_APS_MULTISOURCE_ADMISSION = "aps_multisource_admission"
APS_MULTISOURCE_SCHEMA_ID = "layer3.aps_multisource_admission.v1"
APS_MULTISOURCE_SCHEMA_VERSION = 1
APS_MULTISOURCE_GROUPING_CONTRACT_ID = "layer3_aps_multisource_grouping_v1"
SOURCE_GATE_D_APS_MULTISOURCE_FREEZE = "14_GATED_APS_MULTISOURCE_FREEZE"

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


class Layer3ApsMultisourceError(ValueError):
    pass


@dataclass(frozen=True)
class Layer3ApsMultisourceResult:
    output_package: L3OutputPackage
    admission_payload: dict[str, Any]


def _stable_json_text(payload: Any) -> str:
    return json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False)


def _stable_json_bytes(payload: Any) -> bytes:
    return _stable_json_text(payload).encode("utf-8")


def _stable_hash(payload: Any) -> str:
    return hashlib.sha256(_stable_json_bytes(payload)).hexdigest()


def _json_clone(payload: Any) -> Any:
    return json.loads(_stable_json_text(payload))


def _safe_token(value: str) -> str:
    raw = str(value or "").strip() or "unknown"
    return "".join(char for char in raw if char.isalnum() or char in {"_", "-", "."}) or "unknown"


def _artifact_dir() -> Path:
    path = Path(settings.artifact_storage_dir) / "layer3"
    path.mkdir(parents=True, exist_ok=True)
    return path


def _artifact_path(*, session_id: str, payload_hash: str) -> Path:
    return _artifact_dir() / f"l3_aps_multisource_{_safe_token(session_id)}_{payload_hash[:12]}.json"


def _persist_payload(*, session_id: str, payload: dict[str, Any]) -> tuple[str, str]:
    payload_bytes = _stable_json_bytes(payload)
    payload_hash = hashlib.sha256(payload_bytes).hexdigest()
    payload_path = _artifact_path(session_id=session_id, payload_hash=payload_hash)
    if not payload_path.exists():
        payload_path.write_bytes(payload_bytes)
    return str(payload_path), payload_hash


def _require_existing_ref(ref: str | None, *, label: str) -> str:
    normalized = str(ref or "").strip()
    if not normalized:
        raise Layer3ApsMultisourceError(f"{label} is missing")
    if not Path(normalized).exists():
        raise Layer3ApsMultisourceError(f"{label} does not exist: {normalized}")
    return normalized


def _load_session_or_raise(db: Session, *, session_id: str) -> L3Session:
    session = db.get(L3Session, session_id)
    if session is None:
        raise Layer3ApsMultisourceError(f"Layer 3 session '{session_id}' was not found")
    if session.status not in TERMINAL_SESSION_STATUSES or session.completed_at is None:
        raise Layer3ApsMultisourceError(
            f"Layer 3 session '{session_id}' must be terminal before Gate D APS multisource admission"
        )
    return session


def _load_source_package_or_raise(
    db: Session,
    *,
    session_id: str,
) -> tuple[L3OutputPackage, L3ReconciliationRecord, dict[str, Any]]:
    rows = (
        db.query(L3OutputPackage)
        .filter(L3OutputPackage.session_id == session_id)
        .order_by(L3OutputPackage.package_kind.asc())
        .all()
    )
    rows_by_kind = {row.package_kind: row for row in rows}
    if PACKAGE_KIND_APS_MULTISOURCE_ADMISSION in rows_by_kind:
        raise Layer3ApsMultisourceError(
            f"Layer 3 session '{session_id}' already has an APS multisource admission package"
        )
    source_row = rows_by_kind.get(PACKAGE_KIND_CANONICAL_INTERNAL)
    if source_row is None:
        raise Layer3ApsMultisourceError(
            f"Layer 3 session '{session_id}' is missing the canonical package required for APS multisource admission"
        )
    if source_row.status not in ACCEPTED_SOURCE_PACKAGE_STATUSES:
        raise Layer3ApsMultisourceError(
            f"Layer 3 package '{PACKAGE_KIND_CANONICAL_INTERNAL}' must be complete before APS multisource admission"
        )
    canonical_ref = _require_existing_ref(
        source_row.payload_ref,
        label=f"Layer 3 package '{PACKAGE_KIND_CANONICAL_INTERNAL}' payload ref",
    )
    try:
        canonical_payload = json.loads(Path(canonical_ref).read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise Layer3ApsMultisourceError(
            f"Layer 3 package '{PACKAGE_KIND_CANONICAL_INTERNAL}' payload ref is not valid JSON"
        ) from exc
    package_header = dict(canonical_payload.get("package_header") or {})
    if str(package_header.get("package_kind") or "").strip() != PACKAGE_KIND_CANONICAL_INTERNAL:
        raise Layer3ApsMultisourceError(
            f"Layer 3 package '{PACKAGE_KIND_CANONICAL_INTERNAL}' has incompatible package header provenance"
        )
    selection_summary = dict(canonical_payload.get("selection_and_source_summary") or {})
    if not str(selection_summary.get("selection_manifest_id") or "").strip():
        raise Layer3ApsMultisourceError(
            f"Layer 3 package '{PACKAGE_KIND_CANONICAL_INTERNAL}' is missing selection_manifest_id required for APS multisource admission"
        )
    reconciliation_record_id = str(source_row.reconciliation_record_id or "").strip()
    reconciliation = db.get(L3ReconciliationRecord, reconciliation_record_id)
    if reconciliation is None or reconciliation.session_id != session_id:
        raise Layer3ApsMultisourceError(
            f"Layer 3 session '{session_id}' is missing reconciliation provenance required for APS multisource admission"
        )
    return source_row, reconciliation, canonical_payload


def _load_aps_snapshots_or_raise(db: Session, *, session_id: str) -> list[L3MaterialSnapshot]:
    rows = (
        db.query(L3MaterialSnapshot)
        .filter(
            L3MaterialSnapshot.session_id == session_id,
            L3MaterialSnapshot.source_shape == "aps_content_document",
        )
        .order_by(L3MaterialSnapshot.descriptor_id.asc(), L3MaterialSnapshot.material_snapshot_id.asc())
        .all()
    )
    if not rows:
        raise Layer3ApsMultisourceError(
            f"Layer 3 session '{session_id}' has no APS content snapshots required for multisource admission"
        )
    for row in rows:
        _require_existing_ref(
            row.payload_ref,
            label=f"Layer 3 material snapshot '{row.material_snapshot_id}' payload ref",
        )
    return rows


def _source_identity_or_raise(snapshot: L3MaterialSnapshot) -> tuple[str, str, str]:
    source_identity = dict(snapshot.source_identity_json or {})
    run_id = str(source_identity.get("run_id") or "").strip()
    target_id = str(source_identity.get("target_id") or "").strip()
    content_id = str(source_identity.get("content_id") or "").strip()
    if not run_id:
        raise Layer3ApsMultisourceError(
            f"Layer 3 material snapshot '{snapshot.material_snapshot_id}' is missing source_identity_json.run_id required for APS multisource admission"
        )
    if not target_id:
        raise Layer3ApsMultisourceError(
            f"Layer 3 material snapshot '{snapshot.material_snapshot_id}' is missing source_identity_json.target_id required for APS multisource admission"
        )
    if not content_id:
        raise Layer3ApsMultisourceError(
            f"Layer 3 material snapshot '{snapshot.material_snapshot_id}' is missing source_identity_json.content_id required for APS multisource admission"
        )
    return run_id, target_id, content_id


def _admitted_groups_or_raise(snapshots: list[L3MaterialSnapshot]) -> list[dict[str, Any]]:
    grouped: dict[str, list[L3MaterialSnapshot]] = {}
    for snapshot in snapshots:
        group_id = str(snapshot.co_retrieval_group_id or "").strip() or snapshot.material_snapshot_id
        grouped.setdefault(group_id, []).append(snapshot)

    admitted_groups: list[dict[str, Any]] = []
    for co_retrieval_group_id, bucket in sorted(grouped.items()):
        if len(bucket) < 2:
            continue
        run_ids: set[str] = set()
        descriptor_ids: set[str] = set()
        seen_source_keys: set[tuple[str, str]] = set()
        source_rows: list[dict[str, Any]] = []
        for snapshot in sorted(
            bucket,
            key=lambda row: (
                row.descriptor_id,
                row.material_snapshot_id,
            ),
        ):
            run_id, target_id, content_id = _source_identity_or_raise(snapshot)
            run_ids.add(run_id)
            descriptor_ids.add(str(snapshot.descriptor_id))
            source_key = (target_id, content_id)
            if source_key in seen_source_keys:
                raise Layer3ApsMultisourceError(
                    f"Layer 3 co-retrieval group '{co_retrieval_group_id}' has duplicate APS source identity '{target_id}:{content_id}'"
                )
            seen_source_keys.add(source_key)
            source_rows.append(
                {
                    "material_snapshot_id": snapshot.material_snapshot_id,
                    "descriptor_id": snapshot.descriptor_id,
                    "source_plane": snapshot.source_plane,
                    "source_shape": snapshot.source_shape,
                    "co_retrieval_group_id": co_retrieval_group_id,
                    "run_id": run_id,
                    "target_id": target_id,
                    "content_id": content_id,
                    "payload_ref": snapshot.payload_ref,
                    "payload_hash": snapshot.payload_hash,
                    "source_identity_json": _json_clone(snapshot.source_identity_json or {}),
                    "source_provenance_json": _json_clone(snapshot.source_provenance_json or {}),
                }
            )
        if len(run_ids) != 1:
            raise Layer3ApsMultisourceError(
                f"Layer 3 co-retrieval group '{co_retrieval_group_id}' spans multiple APS run ids and cannot be admitted"
            )
        owner_run_id = next(iter(run_ids))
        source_rows = sorted(
            source_rows,
            key=lambda row: (
                row["target_id"],
                row["content_id"],
                row["material_snapshot_id"],
            ),
        )
        admitted_group_id = _stable_hash(
            {
                "grouping_contract_id": APS_MULTISOURCE_GROUPING_CONTRACT_ID,
                "co_retrieval_group_id": co_retrieval_group_id,
                "owner_run_id": owner_run_id,
                "sources": [
                    {
                        "target_id": row["target_id"],
                        "content_id": row["content_id"],
                        "payload_hash": row["payload_hash"],
                    }
                    for row in source_rows
                ],
            }
        )
        admitted_groups.append(
            {
                "admission_group_id": admitted_group_id,
                "co_retrieval_group_id": co_retrieval_group_id,
                "owner_run_id": owner_run_id,
                "descriptor_ids_json": sorted(descriptor_ids),
                "source_count": len(source_rows),
                "source_identity_keys_json": [
                    {
                        "target_id": row["target_id"],
                        "content_id": row["content_id"],
                    }
                    for row in source_rows
                ],
                "sources": source_rows,
            }
        )

    if not admitted_groups:
        raise Layer3ApsMultisourceError(
            "Layer 3 session does not contain an APS same-run multisource group that can be admitted on existing durable surfaces"
        )
    return admitted_groups


def _build_admission_payload(
    *,
    session: L3Session,
    canonical_payload: dict[str, Any],
    admitted_groups: list[dict[str, Any]],
) -> dict[str, Any]:
    selection_summary = dict(canonical_payload.get("selection_and_source_summary") or {})
    owner_run_ids = sorted({group["owner_run_id"] for group in admitted_groups})
    admitted_source_count = sum(int(group.get("source_count") or 0) for group in admitted_groups)
    return {
        "schema_id": APS_MULTISOURCE_SCHEMA_ID,
        "schema_version": APS_MULTISOURCE_SCHEMA_VERSION,
        "grouping_contract_id": APS_MULTISOURCE_GROUPING_CONTRACT_ID,
        "source_gate": SOURCE_GATE_D_APS_MULTISOURCE_FREEZE,
        "session_id": session.session_id,
        "session_status": session.status,
        "selection_manifest_id": str(selection_summary.get("selection_manifest_id") or ""),
        "selection_hash": str(selection_summary.get("selection_hash") or ""),
        "source_family": "aps_content_document",
        "admitted_group_count": len(admitted_groups),
        "admitted_source_count": admitted_source_count,
        "owner_run_ids_json": owner_run_ids,
        "admitted_groups": _json_clone(admitted_groups),
        "deferred_downstream_families_json": [
            "evidence_report_export_package",
            "context_packet_package",
            "context_dossier",
            "deterministic_insight_artifact",
            "deterministic_challenge_artifact",
            "deterministic_challenge_review_packet",
        ],
    }


def _summary_json(
    *,
    source_row: L3OutputPackage,
    admission_payload: dict[str, Any],
    payload_ref: str,
) -> dict[str, Any]:
    return {
        "package_kind": PACKAGE_KIND_APS_MULTISOURCE_ADMISSION,
        "package_status": source_row.status,
        "source_gate": SOURCE_GATE_D_APS_MULTISOURCE_FREEZE,
        "schema_id": APS_MULTISOURCE_SCHEMA_ID,
        "schema_version": APS_MULTISOURCE_SCHEMA_VERSION,
        "aps_target_family": "multisource_admission",
        "grouping_contract_id": APS_MULTISOURCE_GROUPING_CONTRACT_ID,
        "admission_ref": payload_ref,
        "admitted_group_count": int(admission_payload.get("admitted_group_count") or 0),
        "admitted_source_count": int(admission_payload.get("admitted_source_count") or 0),
        "owner_run_ids_json": list(admission_payload.get("owner_run_ids_json") or []),
        "admission_group_ids_json": [
            str(group.get("admission_group_id") or "")
            for group in list(admission_payload.get("admitted_groups") or [])
        ],
        "source_package_kinds_json": [PACKAGE_KIND_CANONICAL_INTERNAL],
        "source_package_refs_json": {
            PACKAGE_KIND_CANONICAL_INTERNAL: str(source_row.payload_ref or ""),
        },
        "compatibility_notes_json": [
            "aps_multisource_admission points at a persisted Layer 3 artifact summarizing admissible same-run APS source groups",
            "canonical_internal remains the required source package for this tranche",
            "co_retrieval_group_id plus APS source identity are reused without schema widening",
            "connector-run runtime refs remain untouched in this Layer 3 admission path",
        ],
        "field_map_json": {
            "material_snapshots[].co_retrieval_group_id": "admitted_groups[].co_retrieval_group_id",
            "material_snapshots[].source_identity_json.run_id": "admitted_groups[].owner_run_id",
            "material_snapshots[].source_identity_json.target_id": "admitted_groups[].sources[].target_id",
            "material_snapshots[].source_identity_json.content_id": "admitted_groups[].sources[].content_id",
        },
        "handoff_status": {
            "status": "aps_multisource_admitted",
            "aps_multisource_admitted": True,
            "runtime_db_writes_performed": False,
            "admitted_group_count": int(admission_payload.get("admitted_group_count") or 0),
            "admitted_source_count": int(admission_payload.get("admitted_source_count") or 0),
            "owner_run_ids_json": list(admission_payload.get("owner_run_ids_json") or []),
            "source_family": str(admission_payload.get("source_family") or ""),
        },
    }


def materialize_aps_multisource_admission(
    db: Session,
    *,
    session_id: str,
) -> Layer3ApsMultisourceResult:
    session = _load_session_or_raise(db, session_id=session_id)
    source_row, reconciliation, canonical_payload = _load_source_package_or_raise(
        db,
        session_id=session.session_id,
    )
    aps_snapshots = _load_aps_snapshots_or_raise(db, session_id=session.session_id)
    admitted_groups = _admitted_groups_or_raise(aps_snapshots)
    admission_payload = _build_admission_payload(
        session=session,
        canonical_payload=canonical_payload,
        admitted_groups=admitted_groups,
    )
    payload_ref, payload_hash = _persist_payload(
        session_id=session.session_id,
        payload=admission_payload,
    )
    output_package = L3OutputPackage(
        output_package_id=uuid_str(),
        session_id=session.session_id,
        reconciliation_record_id=reconciliation.reconciliation_record_id,
        package_kind=PACKAGE_KIND_APS_MULTISOURCE_ADMISSION,
        status=source_row.status,
        payload_ref=payload_ref,
        payload_hash=payload_hash,
        summary_json=_summary_json(
            source_row=source_row,
            admission_payload=admission_payload,
            payload_ref=payload_ref,
        ),
    )
    db.add(output_package)
    db.flush()
    return Layer3ApsMultisourceResult(
        output_package=output_package,
        admission_payload=admission_payload,
    )
