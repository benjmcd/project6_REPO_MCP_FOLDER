from __future__ import annotations

import hashlib
import json
from collections import Counter
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Sequence

from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.models import (
    L3Descriptor,
    L3MaterialSnapshot,
    L3RetrievalEvent,
    L3SelectionManifest,
    L3Session,
    uuid_str,
)

SESSION_STATUS_ACTIVE_LOADING = "active_loading"
SESSION_STATUS_COMPLETED = "completed"
SESSION_STATUS_COMPLETED_WITH_WARNINGS = "completed_with_warnings"
SESSION_STATUS_FAILED = "failed"

DESCRIPTOR_STATUS_VALUES = frozenset(
    {
        "expanded",
        "resolved_loaded",
        "resolved_empty",
        "resolved_partial",
        "ambiguous",
        "unsupported",
        "failed",
        "skipped",
    }
)
RETRIEVAL_OUTCOME_VALUES = frozenset({"loaded", "empty", "partial", "ambiguous", "unsupported", "failed", "skipped"})


class Layer3SessionEntryError(ValueError):
    pass


@dataclass(frozen=True)
class SessionEntryRequest:
    manifest_items: list[dict[str, Any]]
    source_plane_hints: dict[str, Any]
    commit_reason: str
    entry_route_context: dict[str, Any] = field(default_factory=dict)
    operator_context: dict[str, Any] = field(default_factory=dict)
    summary: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class SnapshotMaterial:
    source_shape: str
    source_identity: dict[str, Any]
    source_provenance: dict[str, Any]
    payload: Any
    load_summary: dict[str, Any] = field(default_factory=dict)
    co_retrieval_group_id: str | None = None


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _stable_json_bytes(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def _json_clone(value: Any) -> Any:
    return json.loads(_stable_json_bytes(value).decode("utf-8"))


def _hash_json(value: Any) -> str:
    return hashlib.sha256(_stable_json_bytes(value)).hexdigest()


def _default_storage_root() -> Path:
    return Path(settings.artifact_storage_dir) / "layer3"


def _validate_descriptor_status(value: str) -> str:
    if value not in DESCRIPTOR_STATUS_VALUES:
        allowed = ", ".join(sorted(DESCRIPTOR_STATUS_VALUES))
        raise Layer3SessionEntryError(f"descriptor status must be one of: {allowed}")
    return value


def _validate_retrieval_outcome(value: str) -> str:
    if value not in RETRIEVAL_OUTCOME_VALUES:
        allowed = ", ".join(sorted(RETRIEVAL_OUTCOME_VALUES))
        raise Layer3SessionEntryError(f"retrieval outcome must be one of: {allowed}")
    return value


def _descriptor_status_for_outcome(outcome: str) -> str:
    mapping = {
        "loaded": "resolved_loaded",
        "empty": "resolved_empty",
        "partial": "resolved_partial",
        "ambiguous": "ambiguous",
        "unsupported": "unsupported",
        "failed": "failed",
        "skipped": "skipped",
    }
    return mapping[outcome]


def _prepare_manifest_json(manifest_items: list[dict[str, Any]]) -> dict[str, Any]:
    if not manifest_items:
        raise Layer3SessionEntryError("manifest_items must contain at least one committed selection")
    return {"items": _json_clone(manifest_items)}


def commit_selection(db: Session, request: SessionEntryRequest) -> tuple[L3Session, L3SelectionManifest]:
    manifest_json = _prepare_manifest_json(request.manifest_items)
    selection_manifest_id = uuid_str()
    session_id = uuid_str()
    now = _utcnow()
    selection_hash = _hash_json(
        {
            "manifest_json": manifest_json,
            "source_plane_hints_json": request.source_plane_hints,
        }
    )

    session = L3Session(
        session_id=session_id,
        created_at=now,
        started_at=now,
        completed_at=None,
        status=SESSION_STATUS_ACTIVE_LOADING,
        selection_manifest_id=selection_manifest_id,
        entry_route_context_json=_json_clone(request.entry_route_context),
        operator_context_json=_json_clone(request.operator_context),
        summary_json=_json_clone(request.summary),
    )
    manifest = L3SelectionManifest(
        selection_manifest_id=selection_manifest_id,
        session_id=session_id,
        manifest_json=manifest_json,
        source_plane_hints_json=_json_clone(request.source_plane_hints),
        selection_hash=selection_hash,
        committed_at=now,
        commit_reason=request.commit_reason,
    )
    db.add(session)
    db.add(manifest)
    db.flush()
    return session, manifest


def _normalized_expansion(
    raw_item: Any,
    *,
    manifest_index: int,
    expansion_index: int,
) -> dict[str, Any]:
    if not isinstance(raw_item, dict):
        return {
            "source_plane": "invalid_selection",
            "descriptor_type": "invalid_selection",
            "selector_payload_json": {"raw_item": repr(raw_item)},
            "selection_basis_json": {
                "manifest_index": manifest_index,
                "expansion_index": expansion_index,
                "error": "selection_item_not_a_mapping",
            },
            "expansion_reason": "invalid_selection",
            "status": "failed",
        }

    source_plane = raw_item.get("source_plane")
    descriptor_type = raw_item.get("descriptor_type")
    selector_payload = raw_item.get("selector_payload")
    selection_basis = raw_item.get("selection_basis")
    expansion_reason = raw_item.get("expansion_reason")
    status = raw_item.get("status") or "expanded"

    if not isinstance(source_plane, str) or not source_plane or not isinstance(descriptor_type, str) or not descriptor_type:
        return {
            "source_plane": str(source_plane or "invalid_selection"),
            "descriptor_type": str(descriptor_type or "invalid_selection"),
            "selector_payload_json": _json_clone(selector_payload if isinstance(selector_payload, dict) else {"raw_item": raw_item}),
            "selection_basis_json": {
                "manifest_index": manifest_index,
                "expansion_index": expansion_index,
                "error": "missing_source_plane_or_descriptor_type",
            },
            "expansion_reason": "invalid_selection",
            "status": "failed",
        }

    if not isinstance(selector_payload, dict):
        selector_payload = {}
    if not isinstance(selection_basis, dict):
        selection_basis = {"manifest_index": manifest_index, "expansion_index": expansion_index}
    if not isinstance(expansion_reason, str) or not expansion_reason:
        expansion_reason = "manifest_expansion"

    return {
        "source_plane": source_plane,
        "descriptor_type": descriptor_type,
        "selector_payload_json": _json_clone(selector_payload),
        "selection_basis_json": _json_clone(selection_basis),
        "expansion_reason": expansion_reason,
        "status": _validate_descriptor_status(str(status)),
    }


def expand_descriptors(db: Session, *, session: L3Session, manifest: L3SelectionManifest) -> list[L3Descriptor]:
    manifest_items = manifest.manifest_json.get("items")
    if not isinstance(manifest_items, list) or not manifest_items:
        raise Layer3SessionEntryError("manifest_json.items must contain at least one committed selection")

    descriptors: list[L3Descriptor] = []
    for manifest_index, manifest_item in enumerate(manifest_items):
        expansions = manifest_item.get("expansions") if isinstance(manifest_item, dict) else None
        expansion_items = expansions if isinstance(expansions, list) and expansions else [manifest_item]
        for expansion_index, expansion_item in enumerate(expansion_items):
            normalized = _normalized_expansion(
                expansion_item,
                manifest_index=manifest_index,
                expansion_index=expansion_index,
            )
            descriptor_hash = _hash_json(
                {
                    "session_id": session.session_id,
                    "source_plane": normalized["source_plane"],
                    "descriptor_type": normalized["descriptor_type"],
                    "selector_payload_json": normalized["selector_payload_json"],
                    "selection_basis_json": normalized["selection_basis_json"],
                    "expansion_reason": normalized["expansion_reason"],
                }
            )
            descriptor = L3Descriptor(
                descriptor_id=uuid_str(),
                session_id=session.session_id,
                selection_manifest_id=manifest.selection_manifest_id,
                source_plane=normalized["source_plane"],
                descriptor_type=normalized["descriptor_type"],
                selector_payload_json=normalized["selector_payload_json"],
                selection_basis_json=normalized["selection_basis_json"],
                expansion_reason=normalized["expansion_reason"],
                status=normalized["status"],
                descriptor_hash=descriptor_hash,
            )
            db.add(descriptor)
            descriptors.append(descriptor)

    db.flush()
    return descriptors


def _material_path(storage_root: Path, *, session_id: str, payload_hash: str) -> Path:
    return storage_root / session_id / f"{payload_hash}.json"


def _persist_material_payload(storage_root: Path, *, session_id: str, payload: Any) -> tuple[str, str]:
    payload_bytes = _stable_json_bytes(payload)
    payload_hash = hashlib.sha256(payload_bytes).hexdigest()
    payload_path = _material_path(storage_root, session_id=session_id, payload_hash=payload_hash)
    payload_path.parent.mkdir(parents=True, exist_ok=True)
    if not payload_path.exists():
        payload_path.write_bytes(payload_bytes)
    return str(payload_path), payload_hash


def _validate_retrieval_payload(
    *,
    outcome: str,
    loaded_materials: Sequence[SnapshotMaterial],
    failed_items: Sequence[dict[str, Any]],
) -> None:
    if outcome == "loaded" and not loaded_materials:
        raise Layer3SessionEntryError("loaded outcome requires at least one snapshot material")
    if outcome in {"empty", "ambiguous", "unsupported", "failed", "skipped"} and loaded_materials:
        raise Layer3SessionEntryError(f"{outcome} outcome must not persist snapshot material")
    if outcome == "partial" and not loaded_materials:
        raise Layer3SessionEntryError("partial outcome requires at least one loaded snapshot material")
    if outcome == "partial" and not failed_items:
        raise Layer3SessionEntryError("partial outcome requires explicit failed_items")


def record_retrieval_event(
    db: Session,
    *,
    session: L3Session,
    descriptor: L3Descriptor,
    outcome: str,
    reason_code: str,
    loaded_materials: Sequence[SnapshotMaterial],
    failed_items: Sequence[dict[str, Any]] | None = None,
    storage_root: Path | None = None,
) -> tuple[L3RetrievalEvent, list[L3MaterialSnapshot]]:
    validated_outcome = _validate_retrieval_outcome(outcome)
    normalized_failed_items = [_json_clone(item) for item in (failed_items or [])]
    _validate_retrieval_payload(
        outcome=validated_outcome,
        loaded_materials=loaded_materials,
        failed_items=normalized_failed_items,
    )

    event_id = uuid_str()
    root = _default_storage_root() if storage_root is None else Path(storage_root)
    snapshots: list[L3MaterialSnapshot] = []
    loaded_items_payload: list[dict[str, Any]] = []

    for material in loaded_materials:
        payload_ref, payload_hash = _persist_material_payload(root, session_id=session.session_id, payload=material.payload)
        snapshot = L3MaterialSnapshot(
            material_snapshot_id=uuid_str(),
            session_id=session.session_id,
            descriptor_id=descriptor.descriptor_id,
            source_plane=descriptor.source_plane,
            source_shape=material.source_shape,
            payload_ref=payload_ref,
            payload_hash=payload_hash,
            source_identity_json=_json_clone(material.source_identity),
            source_provenance_json=_json_clone(material.source_provenance),
            co_retrieval_group_id=material.co_retrieval_group_id or event_id,
            load_summary_json=_json_clone(material.load_summary),
        )
        db.add(snapshot)
        snapshots.append(snapshot)
        loaded_items_payload.append(
            {
                "material_snapshot_id": snapshot.material_snapshot_id,
                "source_plane": snapshot.source_plane,
                "source_shape": snapshot.source_shape,
                "payload_ref": payload_ref,
                "payload_hash": payload_hash,
            }
        )

    descriptor.status = _descriptor_status_for_outcome(validated_outcome)
    retrieval_event = L3RetrievalEvent(
        retrieval_event_id=event_id,
        session_id=session.session_id,
        descriptor_id=descriptor.descriptor_id,
        outcome=validated_outcome,
        reason_code=reason_code,
        material_snapshot_ids_json=[snapshot.material_snapshot_id for snapshot in snapshots],
        event_payload_json={
            "loaded_items": loaded_items_payload,
            "failed_items": normalized_failed_items,
            "why": reason_code,
        },
        occurred_at=_utcnow(),
    )
    db.add(retrieval_event)
    db.flush()
    return retrieval_event, snapshots


def finalize_session(db: Session, *, session: L3Session) -> L3Session:
    descriptors = db.query(L3Descriptor).filter(L3Descriptor.session_id == session.session_id).all()
    retrieval_events = db.query(L3RetrievalEvent).filter(L3RetrievalEvent.session_id == session.session_id).all()

    descriptor_status_counts = Counter(descriptor.status for descriptor in descriptors)
    retrieval_outcome_counts = Counter(event.outcome for event in retrieval_events)
    source_planes = sorted({descriptor.source_plane for descriptor in descriptors})
    loaded_snapshot_count = sum(len(event.material_snapshot_ids_json or []) for event in retrieval_events)
    warning_reasons = sorted({event.reason_code for event in retrieval_events if event.outcome != "loaded"})

    if retrieval_events and all(event.outcome == "loaded" for event in retrieval_events):
        final_status = SESSION_STATUS_COMPLETED
    elif retrieval_events and any(event.outcome == "loaded" for event in retrieval_events):
        final_status = SESSION_STATUS_COMPLETED_WITH_WARNINGS
    else:
        final_status = SESSION_STATUS_FAILED

    session.status = final_status
    session.completed_at = _utcnow()
    session.summary_json = {
        **_json_clone(session.summary_json),
        "descriptor_status_counts": dict(sorted(descriptor_status_counts.items())),
        "retrieval_outcome_counts": dict(sorted(retrieval_outcome_counts.items())),
        "loaded_snapshot_count": loaded_snapshot_count,
        "source_planes": source_planes,
        "warning_reasons": warning_reasons,
    }
    db.flush()
    return session
