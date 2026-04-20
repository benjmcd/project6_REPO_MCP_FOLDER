from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from sqlalchemy import and_
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models import ApsContentChunk, ApsContentDocument, ApsContentLinkage
from app.models.models import L3OutputPackage, L3ReconciliationRecord, L3Session, uuid_str
from app.services import nrc_aps_evidence_bundle as aps_bundle
from app.services import nrc_aps_evidence_bundle_contract as aps_contract
from app.services.layer3_package_entry import (
    PACKAGE_KIND_CANONICAL_INTERNAL,
    PACKAGE_KIND_REVIEW_FACING,
    PACKAGE_KIND_USER_FACING,
    PACKAGE_STATUS_COMPLETE,
    PACKAGE_STATUS_COMPLETE_WITH_WARNINGS,
)
from app.services.layer3_session_entry import (
    SESSION_STATUS_COMPLETED,
    SESSION_STATUS_COMPLETED_WITH_WARNINGS,
    SESSION_STATUS_FAILED,
)


PACKAGE_KIND_APS_EVIDENCE_BUNDLE_HANDOFF = "aps_evidence_bundle_handoff"
APS_HANDOFF_SCHEMA_ID = "layer3.aps_evidence_bundle_handoff.v1"
APS_HANDOFF_SCHEMA_VERSION = 1
SOURCE_GATE_D_APS_HANDOFF_FREEZE = "09_GATED_APS_HANDOFF_FREEZE"

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
REQUIRED_SOURCE_PACKAGE_KINDS = (
    PACKAGE_KIND_CANONICAL_INTERNAL,
    PACKAGE_KIND_USER_FACING,
    PACKAGE_KIND_REVIEW_FACING,
)


class Layer3ApsHandoffError(ValueError):
    pass


@dataclass(frozen=True)
class Layer3ApsHandoffResult:
    output_package: L3OutputPackage
    bundle_payload: dict[str, Any]


def _utc_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _require_existing_ref(ref: str | None, *, label: str) -> str:
    normalized = str(ref or "").strip()
    if not normalized:
        raise Layer3ApsHandoffError(f"{label} is missing")
    if not Path(normalized).exists():
        raise Layer3ApsHandoffError(f"{label} does not exist: {normalized}")
    return normalized


def _read_json_dict(path: str | Path, *, label: str) -> dict[str, Any]:
    target = Path(path)
    try:
        payload = json.loads(target.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise Layer3ApsHandoffError(f"{label} is unreadable: {target}") from exc
    if not isinstance(payload, dict):
        raise Layer3ApsHandoffError(f"{label} is not a JSON object: {target}")
    return payload


def _load_session_or_raise(db: Session, *, session_id: str) -> L3Session:
    session = db.get(L3Session, session_id)
    if session is None:
        raise Layer3ApsHandoffError(f"Layer 3 session '{session_id}' was not found")
    if session.status not in TERMINAL_SESSION_STATUSES or session.completed_at is None:
        raise Layer3ApsHandoffError(
            f"Layer 3 session '{session_id}' must be terminal before Gate D APS handoff"
        )
    return session


def _load_reconciliation_or_raise(
    db: Session,
    *,
    session_id: str,
    reconciliation_record_id: str,
) -> L3ReconciliationRecord:
    reconciliation = db.get(L3ReconciliationRecord, reconciliation_record_id)
    if reconciliation is None or reconciliation.session_id != session_id:
        raise Layer3ApsHandoffError(
            f"Layer 3 session '{session_id}' is missing the reconciliation record required for APS handoff"
        )
    return reconciliation


def _load_source_packages_or_raise(
    db: Session,
    *,
    session_id: str,
) -> tuple[dict[str, L3OutputPackage], L3ReconciliationRecord]:
    rows = (
        db.query(L3OutputPackage)
        .filter(L3OutputPackage.session_id == session_id)
        .order_by(L3OutputPackage.package_kind.asc())
        .all()
    )
    rows_by_kind = {row.package_kind: row for row in rows}
    if PACKAGE_KIND_APS_EVIDENCE_BUNDLE_HANDOFF in rows_by_kind:
        raise Layer3ApsHandoffError(
            f"Layer 3 session '{session_id}' already has an APS evidence-bundle handoff package"
        )
    missing = [kind for kind in REQUIRED_SOURCE_PACKAGE_KINDS if kind not in rows_by_kind]
    if missing:
        raise Layer3ApsHandoffError(
            f"Layer 3 session '{session_id}' is missing required package(s): {', '.join(missing)}"
        )

    required_rows = {kind: rows_by_kind[kind] for kind in REQUIRED_SOURCE_PACKAGE_KINDS}
    reconciliation_ids = {
        str(row.reconciliation_record_id or "").strip()
        for row in required_rows.values()
        if str(row.reconciliation_record_id or "").strip()
    }
    if len(reconciliation_ids) != 1:
        raise Layer3ApsHandoffError(
            f"Layer 3 session '{session_id}' has inconsistent reconciliation provenance across source packages"
        )
    for package_kind, row in required_rows.items():
        if row.status not in ACCEPTED_SOURCE_PACKAGE_STATUSES:
            raise Layer3ApsHandoffError(
                f"Layer 3 package '{package_kind}' must be complete before APS handoff"
            )
        _require_existing_ref(row.payload_ref, label=f"Layer 3 package '{package_kind}' payload ref")

    reconciliation = _load_reconciliation_or_raise(
        db,
        session_id=session_id,
        reconciliation_record_id=next(iter(reconciliation_ids)),
    )
    return required_rows, reconciliation


def _canonical_payload_or_raise(canonical_row: L3OutputPackage) -> dict[str, Any]:
    payload = _read_json_dict(
        _require_existing_ref(
            canonical_row.payload_ref,
            label=f"Layer 3 package '{PACKAGE_KIND_CANONICAL_INTERNAL}' payload ref",
        ),
        label=f"Layer 3 package '{PACKAGE_KIND_CANONICAL_INTERNAL}' payload",
    )
    inventory = (
        payload.get("selection_and_source_summary", {})
        if isinstance(payload.get("selection_and_source_summary"), dict)
        else {}
    ).get("material_snapshot_inventory_json")
    if not isinstance(inventory, list):
        raise Layer3ApsHandoffError(
            "canonical_internal package is missing selection_and_source_summary.material_snapshot_inventory_json"
        )
    return payload


def _selected_aps_targets_or_raise(
    canonical_payload: dict[str, Any],
) -> tuple[str, list[dict[str, str]]]:
    inventory = list(
        (
            canonical_payload.get("selection_and_source_summary", {})
            if isinstance(canonical_payload.get("selection_and_source_summary"), dict)
            else {}
        ).get("material_snapshot_inventory_json")
        or []
    )
    selected_targets: list[dict[str, str]] = []
    for item in inventory:
        if not isinstance(item, dict):
            continue
        if str(item.get("source_shape") or "").strip() != "aps_content_document":
            continue
        identity = dict(item.get("source_identity_json") or {})
        content_id = str(identity.get("content_id") or "").strip()
        run_id = str(identity.get("run_id") or "").strip()
        target_id = str(identity.get("target_id") or "").strip()
        if not content_id or not run_id or not target_id:
            raise Layer3ApsHandoffError(
                "canonical_internal package APS source identity must include content_id, run_id, and target_id for APS handoff"
            )
        selected_targets.append(
            {
                "content_id": content_id,
                "run_id": run_id,
                "target_id": target_id,
            }
        )
    if not selected_targets:
        raise Layer3ApsHandoffError(
            "canonical_internal package contains no aps_content_document provenance admitted for APS handoff"
        )

    run_ids = sorted({item["run_id"] for item in selected_targets})
    if len(run_ids) != 1:
        raise Layer3ApsHandoffError(
            "APS handoff requires aps_content_document provenance from exactly one NRC APS run"
        )

    deduped: dict[tuple[str, str, str], dict[str, str]] = {}
    for item in selected_targets:
        deduped[(item["content_id"], item["run_id"], item["target_id"])] = item
    ordered = [deduped[key] for key in sorted(deduped)]
    return run_ids[0], ordered


def _load_base_rows_or_raise(
    db: Session,
    *,
    run_id: str,
    selected_targets: list[dict[str, str]],
) -> list[dict[str, Any]]:
    content_ids = sorted({item["content_id"] for item in selected_targets})
    target_ids = sorted({item["target_id"] for item in selected_targets})
    selected_keys = {(item["content_id"], item["run_id"], item["target_id"]) for item in selected_targets}
    query = (
        db.query(ApsContentLinkage, ApsContentDocument, ApsContentChunk)
        .join(
            ApsContentDocument,
            and_(
                ApsContentDocument.content_id == ApsContentLinkage.content_id,
                ApsContentDocument.content_contract_id == ApsContentLinkage.content_contract_id,
                ApsContentDocument.chunking_contract_id == ApsContentLinkage.chunking_contract_id,
            ),
        )
        .join(
            ApsContentChunk,
            and_(
                ApsContentChunk.content_id == ApsContentLinkage.content_id,
                ApsContentChunk.content_contract_id == ApsContentLinkage.content_contract_id,
                ApsContentChunk.chunking_contract_id == ApsContentLinkage.chunking_contract_id,
            ),
        )
        .filter(ApsContentLinkage.run_id == run_id)
        .filter(ApsContentLinkage.content_id.in_(content_ids))
        .filter(ApsContentLinkage.target_id.in_(target_ids))
        .filter(ApsContentLinkage.content_contract_id == aps_contract.APS_CONTENT_CONTRACT_ID)
        .filter(ApsContentLinkage.chunking_contract_id == aps_contract.APS_CHUNKING_CONTRACT_ID)
        .filter(ApsContentDocument.normalization_contract_id == aps_contract.APS_NORMALIZATION_CONTRACT_ID)
        .order_by(
            ApsContentLinkage.content_id.asc(),
            ApsContentLinkage.target_id.asc(),
            ApsContentChunk.chunk_ordinal.asc(),
            ApsContentChunk.chunk_id.asc(),
        )
    )
    rows: list[dict[str, Any]] = []
    seen_keys: set[tuple[str, str, str]] = set()
    for linkage, document, chunk in query.all():
        row_key = (
            str(linkage.content_id or "").strip(),
            str(linkage.run_id or "").strip(),
            str(linkage.target_id or "").strip(),
        )
        if row_key not in selected_keys:
            continue
        rows.append(aps_bundle._serialize_index_row(linkage=linkage, document=document, chunk=chunk))
        seen_keys.add(row_key)
    if not rows:
        raise Layer3ApsHandoffError(f"NRC APS content rows were not found for Layer 3 session '{run_id}' handoff scope")
    missing = sorted(selected_keys - seen_keys)
    if missing:
        missing_tokens = [f"{content_id}:{target_id}" for content_id, _, target_id in missing]
        raise Layer3ApsHandoffError(
            "APS handoff could not resolve content rows for: " + ", ".join(missing_tokens)
        )
    return rows


def _normalized_request(*, run_id: str, selected_targets: list[dict[str, str]]) -> dict[str, Any]:
    return aps_contract.normalize_request_payload(
        {
            "run_id": run_id,
            "content_ids": [item["content_id"] for item in selected_targets],
            "target_ids": [item["target_id"] for item in selected_targets],
            "content_contract_id": aps_contract.APS_CONTENT_CONTRACT_ID,
            "chunking_contract_id": aps_contract.APS_CHUNKING_CONTRACT_ID,
            "normalization_contract_id": aps_contract.APS_NORMALIZATION_CONTRACT_ID,
            "persist_bundle": True,
        }
    )


def _bundle_payload(
    *,
    run_id: str,
    normalized_request: dict[str, Any],
    ordered_items: list[dict[str, Any]],
) -> dict[str, Any]:
    snapshot_started = _utc_iso()
    index_max_updated = aps_bundle._snapshot_max_updated(ordered_items)
    index_state_payload = {
        "rows": [aps_bundle._index_signature(item) for item in ordered_items],
        "row_count": len(ordered_items),
        "index_max_updated_at_utc": index_max_updated,
    }
    index_state_hash = aps_contract.stable_hash(index_state_payload)
    request_identity = aps_contract.request_identity_hash(normalized_request)
    bundle_id = aps_contract.derive_bundle_id(
        request_identity_hash_value=request_identity,
        index_state_hash=index_state_hash,
    )
    snapshot_completed = _utc_iso()
    payload = {
        "schema_id": aps_contract.APS_EVIDENCE_BUNDLE_SCHEMA_ID,
        "schema_version": aps_contract.APS_EVIDENCE_BUNDLE_SCHEMA_VERSION,
        "generated_at_utc": snapshot_completed,
        "request_contract_id": aps_contract.APS_EVIDENCE_REQUEST_NORM_CONTRACT_ID,
        "ranking_contract_id": aps_contract.APS_EVIDENCE_RANKING_CONTRACT_ID,
        "snippet_contract_id": aps_contract.APS_EVIDENCE_SNIPPET_CONTRACT_ID,
        "snapshot_contract_id": aps_contract.APS_EVIDENCE_SNAPSHOT_CONTRACT_ID,
        "bundle_id": bundle_id,
        "request_identity_hash": request_identity,
        "mode": str(normalized_request.get("mode") or ""),
        "run_id": run_id,
        "query": normalized_request.get("query"),
        "query_tokens": list(normalized_request.get("query_tokens") or []),
        "normalized_request": aps_contract.request_identity_payload(normalized_request),
        "snapshot": {
            "snapshot_contract_id": aps_contract.APS_EVIDENCE_SNAPSHOT_CONTRACT_ID,
            "snapshot_started_at_utc": snapshot_started,
            "snapshot_completed_at_utc": snapshot_completed,
            "index_state_hash": index_state_hash,
            "index_row_count": len(ordered_items),
            "index_max_updated_at_utc": index_max_updated,
            "db_fingerprint": aps_bundle._db_fingerprint(),
            "read_scope": {
                "run_id": run_id,
                "filters": dict(normalized_request.get("filters") or {}),
            },
        },
        "total_hits": len(ordered_items),
        "total_groups": aps_contract.total_group_count(ordered_items),
        "results": ordered_items,
    }
    payload["bundle_checksum"] = aps_contract.compute_bundle_checksum(payload)
    return payload


def _persist_bundle_or_raise(*, run_id: str, payload: dict[str, Any]) -> tuple[dict[str, Any], str]:
    if len(payload["results"]) > aps_contract.APS_MAX_BUNDLE_CHUNKS:
        raise Layer3ApsHandoffError(
            f"APS evidence bundle chunk count exceeds cap ({aps_contract.APS_MAX_BUNDLE_CHUNKS})"
        )
    if len(aps_contract.canonical_json_bytes(payload)) > aps_contract.APS_MAX_BUNDLE_BYTES:
        raise Layer3ApsHandoffError(
            f"APS evidence bundle byte size exceeds cap ({aps_contract.APS_MAX_BUNDLE_BYTES})"
        )
    artifact_path = aps_bundle.bundle_artifact_path(
        run_id=run_id,
        bundle_id=str(payload.get("bundle_id") or ""),
        reports_dir=settings.connector_reports_dir,
    )
    bundle_ref = aps_bundle._persist_or_validate_bundle(artifact_path=artifact_path, payload=payload)
    validated_payload, _ = aps_bundle.load_persisted_bundle_artifact(bundle_ref=bundle_ref)
    return validated_payload, bundle_ref


def _summary_json(
    *,
    source_rows: dict[str, L3OutputPackage],
    bundle_payload: dict[str, Any],
    bundle_ref: str,
    package_status: str,
    run_id: str,
) -> dict[str, Any]:
    return {
        "package_kind": PACKAGE_KIND_APS_EVIDENCE_BUNDLE_HANDOFF,
        "package_status": package_status,
        "source_gate": SOURCE_GATE_D_APS_HANDOFF_FREEZE,
        "aps_target_family": "evidence_bundle",
        "aps_schema_id": aps_contract.APS_EVIDENCE_BUNDLE_SCHEMA_ID,
        "bundle_id": str(bundle_payload.get("bundle_id") or ""),
        "bundle_ref": bundle_ref,
        "bundle_checksum": str(bundle_payload.get("bundle_checksum") or ""),
        "source_package_kinds_json": list(REQUIRED_SOURCE_PACKAGE_KINDS),
        "source_package_refs_json": {
            package_kind: str(source_rows[package_kind].payload_ref or "")
            for package_kind in REQUIRED_SOURCE_PACKAGE_KINDS
        },
        "compatibility_notes_json": [
            "canonical_internal remains the Layer 3 source of truth",
            "aps_evidence_bundle_handoff points at a persisted aps.evidence_bundle.v2 artifact",
            "APS bundle rows are resolved from existing APS content tables using canonical snapshot identities",
        ],
        "field_map_json": {
            "canonical.selection_and_source_summary.material_snapshot_inventory_json[].source_identity_json.run_id": "snapshot.read_scope.run_id",
            "canonical.selection_and_source_summary.material_snapshot_inventory_json[].source_identity_json.target_id": "results[].target_id",
            "canonical.selection_and_source_summary.material_snapshot_inventory_json[].source_identity_json.content_id": "results[].content_id",
            "aps_content_linkage.content_units_ref": "results[].content_units_ref",
            "aps_content_document.normalization_contract_id": "results[].normalization_contract_id",
        },
        "handoff_status": {
            "status": "aps_evidence_bundle_emitted",
            "aps_handoff_admitted": True,
            "canonical_package_status": package_status,
            "bundle_persisted": True,
            "bundle_result_count": int(bundle_payload.get("total_hits") or 0),
            "bundle_group_count": int(bundle_payload.get("total_groups") or 0),
            "source_run_id": run_id,
        },
    }


def materialize_aps_handoff(db: Session, *, session_id: str) -> Layer3ApsHandoffResult:
    session = _load_session_or_raise(db, session_id=session_id)
    source_rows, reconciliation = _load_source_packages_or_raise(db, session_id=session.session_id)
    canonical_payload = _canonical_payload_or_raise(source_rows[PACKAGE_KIND_CANONICAL_INTERNAL])
    run_id, selected_targets = _selected_aps_targets_or_raise(canonical_payload)
    base_rows = _load_base_rows_or_raise(db, run_id=run_id, selected_targets=selected_targets)
    normalized_request = _normalized_request(run_id=run_id, selected_targets=selected_targets)
    try:
        ordered_items = aps_bundle._validated_items_for_mode(
            base_items=base_rows,
            normalized_request=normalized_request,
        )
        for item in ordered_items:
            item.pop("chunk_length", None)
        bundle_payload = _bundle_payload(
            run_id=run_id,
            normalized_request=normalized_request,
            ordered_items=ordered_items,
        )
        validated_payload, bundle_ref = _persist_bundle_or_raise(run_id=run_id, payload=bundle_payload)
    except aps_bundle.EvidenceBundleError as exc:
        raise Layer3ApsHandoffError(
            f"APS evidence bundle handoff failed ({exc.code}): {exc.message or str(exc)}"
        ) from exc
    package_status = source_rows[PACKAGE_KIND_CANONICAL_INTERNAL].status
    output_package = L3OutputPackage(
        output_package_id=uuid_str(),
        session_id=session.session_id,
        reconciliation_record_id=reconciliation.reconciliation_record_id,
        package_kind=PACKAGE_KIND_APS_EVIDENCE_BUNDLE_HANDOFF,
        status=package_status,
        payload_ref=bundle_ref,
        payload_hash=hashlib.sha256(Path(bundle_ref).read_bytes()).hexdigest(),
        summary_json=_summary_json(
            source_rows=source_rows,
            bundle_payload=validated_payload,
            bundle_ref=bundle_ref,
            package_status=package_status,
            run_id=run_id,
        ),
    )
    db.add(output_package)
    db.flush()
    return Layer3ApsHandoffResult(
        output_package=output_package,
        bundle_payload=validated_payload,
    )
