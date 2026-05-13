from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Sequence

from sqlalchemy.orm import Session

from app.models.models import (
    L3AnalysisGroup,
    L3AnalysisSet,
    L3AnalysisUnit,
    L3MaterialSnapshot,
    L3Session,
    L3TypingRecord,
    uuid_str,
)
from app.services.layer3_session_entry import (
    SESSION_STATUS_COMPLETED,
    SESSION_STATUS_COMPLETED_WITH_WARNINGS,
)
from app.services.layer3_source_boundary import SOURCE_INTAKE_GATE_B_SOURCE_CLASS
from app.services.layer3_utils import (
    json_clone as _json_clone,
    stable_hash as _hash_json,
    stable_json_bytes as _stable_json_bytes,
    utcnow as _utcnow,
)

MODALITY_QUANTITATIVE = "quantitative"
MODALITY_QUALITATIVE = "qualitative"
MODALITY_HYBRID = "hybrid"

UNIT_KIND_ATOMIC = "atomic"

GROUP_BASIS_SAME_DESCRIPTOR = "same_descriptor"
GROUP_BASIS_SAME_CO_RETRIEVAL_GROUP = "same_co_retrieval_group"
GROUP_BASIS_SINGLETON = "singleton"

SET_TYPE_SINGLE_ITEM = "single_item"
SET_TYPE_ASSOCIATED_COHORT = "associated_cohort"

GROUP_STATUS_FORMED = "formed"


class Layer3TypingEntryError(ValueError):
    pass


@dataclass(frozen=True)
class _TypingRule:
    planning_shape_family: str
    candidate_modalities: tuple[str, ...]
    chosen_modality: str
    confidence: float
    unit_kind: str = UNIT_KIND_ATOMIC
    confidence_basis: str = "frozen_shape_default"


@dataclass
class _TypedSnapshotEntry:
    snapshot: L3MaterialSnapshot
    rule: _TypingRule
    typing_basis_json: dict[str, Any]
    typing_record: L3TypingRecord | None = None
    analysis_unit: L3AnalysisUnit | None = None


@dataclass(frozen=True)
class _GroupBlueprint:
    analysis_modality: str
    group_basis: str
    analysis_unit_ids: tuple[str, ...]
    descriptor_id: str | None
    co_retrieval_group_id: str | None


@dataclass(frozen=True)
class Layer3TypingEntryResult:
    typing_records: tuple[L3TypingRecord, ...]
    analysis_units: tuple[L3AnalysisUnit, ...]
    analysis_groups: tuple[L3AnalysisGroup, ...]
    analysis_sets: tuple[L3AnalysisSet, ...]


SUPPORTED_TYPING_RULES = {
    "dataset_version": _TypingRule(
        planning_shape_family="tabular_numeric",
        candidate_modalities=(MODALITY_QUANTITATIVE,),
        chosen_modality=MODALITY_QUANTITATIVE,
        confidence=1.0,
    ),
    "aps_content_document": _TypingRule(
        planning_shape_family="document_chunks",
        candidate_modalities=(MODALITY_QUALITATIVE,),
        chosen_modality=MODALITY_QUALITATIVE,
        confidence=1.0,
    ),
    SOURCE_INTAKE_GATE_B_SOURCE_CLASS: _TypingRule(
        planning_shape_family="document_chunks",
        candidate_modalities=(MODALITY_QUALITATIVE,),
        chosen_modality=MODALITY_QUALITATIVE,
        confidence=1.0,
        confidence_basis="frozen_source_intake_text_document_default",
    ),
}

FINALIZED_TYPING_SESSION_STATUSES = frozenset(
    {
        SESSION_STATUS_COMPLETED,
        SESSION_STATUS_COMPLETED_WITH_WARNINGS,
    }
)


def _load_session_or_raise(db: Session, *, session_id: str) -> L3Session:
    session = db.get(L3Session, session_id)
    if session is None:
        raise Layer3TypingEntryError(f"Layer 3 session '{session_id}' was not found")
    if session.status not in FINALIZED_TYPING_SESSION_STATUSES or session.completed_at is None:
        raise Layer3TypingEntryError(
            f"Layer 3 session '{session_id}' must be finalized before Gate C typing entry"
        )
    return session


def _ensure_session_not_yet_typed(db: Session, *, session_id: str) -> None:
    if db.query(L3TypingRecord).filter(L3TypingRecord.session_id == session_id).first() is not None:
        raise Layer3TypingEntryError(f"Layer 3 session '{session_id}' already has typing records")
    if db.query(L3AnalysisUnit).filter(L3AnalysisUnit.session_id == session_id).first() is not None:
        raise Layer3TypingEntryError(f"Layer 3 session '{session_id}' already has analysis units")
    if db.query(L3AnalysisGroup).filter(L3AnalysisGroup.session_id == session_id).first() is not None:
        raise Layer3TypingEntryError(f"Layer 3 session '{session_id}' already has analysis groups")
    if db.query(L3AnalysisSet).filter(L3AnalysisSet.session_id == session_id).first() is not None:
        raise Layer3TypingEntryError(f"Layer 3 session '{session_id}' already has analysis sets")


def _load_snapshots_or_raise(db: Session, *, session_id: str) -> list[L3MaterialSnapshot]:
    snapshots = (
        db.query(L3MaterialSnapshot)
        .filter(L3MaterialSnapshot.session_id == session_id)
        .order_by(L3MaterialSnapshot.descriptor_id.asc(), L3MaterialSnapshot.material_snapshot_id.asc())
        .all()
    )
    if not snapshots:
        raise Layer3TypingEntryError(f"Layer 3 session '{session_id}' has no material snapshots to type")
    return snapshots


def _typing_rule_for_snapshot(snapshot: L3MaterialSnapshot) -> _TypingRule:
    rule = SUPPORTED_TYPING_RULES.get(snapshot.source_shape)
    if rule is None:
        raise Layer3TypingEntryError(
            f"unsupported source_shape '{snapshot.source_shape}' for Gate C typing entry"
        )
    return rule


def _typing_basis_for_snapshot(snapshot: L3MaterialSnapshot, rule: _TypingRule) -> dict[str, Any]:
    return {
        "rule_version": "gatec_first_v1_repo_confirmed_shapes",
        "source_shape": snapshot.source_shape,
        "planning_shape_family": rule.planning_shape_family,
        "candidate_modalities_json": list(rule.candidate_modalities),
        "chosen_modality": rule.chosen_modality,
        "confidence_basis": rule.confidence_basis,
        "descriptor_id": snapshot.descriptor_id,
        "source_plane": snapshot.source_plane,
    }


def _build_entry_candidates(snapshots: Sequence[L3MaterialSnapshot]) -> list[_TypedSnapshotEntry]:
    entries: list[_TypedSnapshotEntry] = []
    for snapshot in snapshots:
        rule = _typing_rule_for_snapshot(snapshot)
        entries.append(
            _TypedSnapshotEntry(
                snapshot=snapshot,
                rule=rule,
                typing_basis_json=_typing_basis_for_snapshot(snapshot, rule),
            )
        )
    return entries


def _materialize_typing_records(db: Session, *, session_id: str, entries: Sequence[_TypedSnapshotEntry]) -> list[L3TypingRecord]:
    created: list[L3TypingRecord] = []
    for entry in entries:
        record = L3TypingRecord(
            typing_record_id=uuid_str(),
            session_id=session_id,
            material_snapshot_id=entry.snapshot.material_snapshot_id,
            candidate_modalities_json=list(entry.rule.candidate_modalities),
            chosen_modality=entry.rule.chosen_modality,
            typing_basis_json=_json_clone(entry.typing_basis_json),
            confidence=entry.rule.confidence,
            overridden_by_operator=False,
            override_reason=None,
            created_at=_utcnow(),
        )
        db.add(record)
        entry.typing_record = record
        created.append(record)
    db.flush()
    return created


def _unit_summary(entry: _TypedSnapshotEntry) -> dict[str, Any]:
    return {
        "source_shape": entry.snapshot.source_shape,
        "source_plane": entry.snapshot.source_plane,
        "descriptor_id": entry.snapshot.descriptor_id,
        "co_retrieval_group_id": entry.snapshot.co_retrieval_group_id,
        "typing_record_id": entry.typing_record.typing_record_id if entry.typing_record is not None else None,
    }


def _unit_hash(entry: _TypedSnapshotEntry) -> str:
    if entry.typing_record is None:
        raise Layer3TypingEntryError("typing record must exist before unit formation")
    return _hash_json(
        {
            "session_id": entry.snapshot.session_id,
            "unit_kind": entry.rule.unit_kind,
            "analysis_modality": entry.rule.chosen_modality,
            "member_snapshot_ids_json": [entry.snapshot.material_snapshot_id],
            "typing_record_ids_json": [entry.typing_record.typing_record_id],
            "must_remain_intact": False,
            "derived_view_ref": None,
        }
    )


def _materialize_analysis_units(
    db: Session,
    *,
    session_id: str,
    entries: Sequence[_TypedSnapshotEntry],
) -> list[L3AnalysisUnit]:
    created: list[L3AnalysisUnit] = []
    for entry in entries:
        if entry.typing_record is None:
            raise Layer3TypingEntryError("typing record must exist before analysis-unit formation")
        member_snapshot_ids = [entry.snapshot.material_snapshot_id]
        typing_record_ids = [entry.typing_record.typing_record_id]
        unit = L3AnalysisUnit(
            analysis_unit_id=uuid_str(),
            session_id=session_id,
            unit_kind=entry.rule.unit_kind,
            analysis_modality=entry.rule.chosen_modality,
            member_snapshot_ids_json=member_snapshot_ids,
            member_ranges_json=[{"material_snapshot_id": entry.snapshot.material_snapshot_id, "scope": "full"}],
            must_remain_intact=False,
            typing_record_ids_json=typing_record_ids,
            derived_view_ref=None,
            unit_hash=_unit_hash(entry),
            summary_json=_unit_summary(entry),
            created_at=_utcnow(),
        )
        db.add(unit)
        entry.analysis_unit = unit
        created.append(unit)
    db.flush()
    return created


def _sorted_entries(entries: Sequence[_TypedSnapshotEntry]) -> tuple[_TypedSnapshotEntry, ...]:
    return tuple(sorted(entries, key=lambda entry: entry.snapshot.material_snapshot_id))


def _group_blueprint(
    entries: Sequence[_TypedSnapshotEntry],
    *,
    analysis_modality: str,
    group_basis: str,
    descriptor_id: str | None,
    co_retrieval_group_id: str | None,
) -> _GroupBlueprint:
    analysis_unit_ids = tuple(
        entry.analysis_unit.analysis_unit_id
        for entry in _sorted_entries(entries)
        if entry.analysis_unit is not None
    )
    if not analysis_unit_ids:
        raise Layer3TypingEntryError("analysis units must exist before group formation")
    return _GroupBlueprint(
        analysis_modality=analysis_modality,
        group_basis=group_basis,
        analysis_unit_ids=analysis_unit_ids,
        descriptor_id=descriptor_id,
        co_retrieval_group_id=co_retrieval_group_id,
    )


def _build_group_blueprints(entries: Sequence[_TypedSnapshotEntry]) -> list[_GroupBlueprint]:
    remaining = list(entries)
    blueprints: list[_GroupBlueprint] = []

    descriptor_buckets: dict[tuple[str, str], list[_TypedSnapshotEntry]] = {}
    for entry in remaining:
        descriptor_buckets.setdefault((entry.rule.chosen_modality, entry.snapshot.descriptor_id), []).append(entry)
    consumed_snapshot_ids: set[str] = set()
    for (analysis_modality, descriptor_id), bucket in sorted(descriptor_buckets.items()):
        if len(bucket) > 1:
            blueprints.append(
                _group_blueprint(
                    bucket,
                    analysis_modality=analysis_modality,
                    group_basis=GROUP_BASIS_SAME_DESCRIPTOR,
                    descriptor_id=descriptor_id,
                    co_retrieval_group_id=None,
                )
            )
            consumed_snapshot_ids.update(entry.snapshot.material_snapshot_id for entry in bucket)
    remaining = [entry for entry in remaining if entry.snapshot.material_snapshot_id not in consumed_snapshot_ids]

    retrieval_buckets: dict[tuple[str, str], list[_TypedSnapshotEntry]] = {}
    for entry in remaining:
        if entry.snapshot.co_retrieval_group_id:
            retrieval_buckets.setdefault(
                (entry.rule.chosen_modality, entry.snapshot.co_retrieval_group_id),
                [],
            ).append(entry)
    consumed_snapshot_ids.clear()
    for (analysis_modality, co_retrieval_group_id), bucket in sorted(retrieval_buckets.items()):
        if len(bucket) > 1:
            blueprints.append(
                _group_blueprint(
                    bucket,
                    analysis_modality=analysis_modality,
                    group_basis=GROUP_BASIS_SAME_CO_RETRIEVAL_GROUP,
                    descriptor_id=None,
                    co_retrieval_group_id=co_retrieval_group_id,
                )
            )
            consumed_snapshot_ids.update(entry.snapshot.material_snapshot_id for entry in bucket)
    remaining = [entry for entry in remaining if entry.snapshot.material_snapshot_id not in consumed_snapshot_ids]

    for entry in _sorted_entries(remaining):
        blueprints.append(
            _group_blueprint(
                [entry],
                analysis_modality=entry.rule.chosen_modality,
                group_basis=GROUP_BASIS_SINGLETON,
                descriptor_id=entry.snapshot.descriptor_id,
                co_retrieval_group_id=entry.snapshot.co_retrieval_group_id,
            )
        )

    return sorted(
        blueprints,
        key=lambda blueprint: (
            blueprint.analysis_modality,
            blueprint.group_basis,
            blueprint.analysis_unit_ids,
        ),
    )


def _group_typing_basis(blueprint: _GroupBlueprint) -> dict[str, Any]:
    return {
        "group_basis": blueprint.group_basis,
        "analysis_modality": blueprint.analysis_modality,
        "descriptor_id": blueprint.descriptor_id,
        "co_retrieval_group_id": blueprint.co_retrieval_group_id,
        "analysis_unit_count": len(blueprint.analysis_unit_ids),
    }


def _materialize_groups_and_sets(
    db: Session,
    *,
    session_id: str,
    blueprints: Sequence[_GroupBlueprint],
) -> tuple[list[L3AnalysisGroup], list[L3AnalysisSet]]:
    groups: list[L3AnalysisGroup] = []
    for blueprint in blueprints:
        group = L3AnalysisGroup(
            analysis_group_id=uuid_str(),
            session_id=session_id,
            analysis_modality=blueprint.analysis_modality,
            typing_basis_json=_group_typing_basis(blueprint),
            analysis_unit_ids_json=list(blueprint.analysis_unit_ids),
            status=GROUP_STATUS_FORMED,
        )
        db.add(group)
        groups.append(group)
    db.flush()

    sets: list[L3AnalysisSet] = []
    for group, blueprint in zip(groups, blueprints, strict=True):
        if len(blueprint.analysis_unit_ids) == 1:
            set_type = SET_TYPE_SINGLE_ITEM
        elif blueprint.group_basis in {GROUP_BASIS_SAME_DESCRIPTOR, GROUP_BASIS_SAME_CO_RETRIEVAL_GROUP}:
            set_type = SET_TYPE_ASSOCIATED_COHORT
        else:
            raise Layer3TypingEntryError(
                "unsupported group formation for first-v1 analysis-set materialization"
            )
        analysis_set = L3AnalysisSet(
            analysis_set_id=uuid_str(),
            session_id=session_id,
            analysis_group_ids_json=[group.analysis_group_id],
            analysis_unit_ids_json=list(blueprint.analysis_unit_ids),
            set_type=set_type,
            formation_basis_json={
                "set_type": set_type,
                "group_basis": blueprint.group_basis,
                "analysis_modality": blueprint.analysis_modality,
                "analysis_group_id": group.analysis_group_id,
            },
            created_at=_utcnow(),
        )
        db.add(analysis_set)
        sets.append(analysis_set)
    db.flush()
    return groups, sets


def materialize_typing_entry(db: Session, *, session_id: str) -> Layer3TypingEntryResult:
    _load_session_or_raise(db, session_id=session_id)
    _ensure_session_not_yet_typed(db, session_id=session_id)
    snapshots = _load_snapshots_or_raise(db, session_id=session_id)

    entries = _build_entry_candidates(snapshots)
    typing_records = _materialize_typing_records(db, session_id=session_id, entries=entries)
    analysis_units = _materialize_analysis_units(db, session_id=session_id, entries=entries)
    group_blueprints = _build_group_blueprints(entries)
    analysis_groups, analysis_sets = _materialize_groups_and_sets(
        db,
        session_id=session_id,
        blueprints=group_blueprints,
    )

    return Layer3TypingEntryResult(
        typing_records=tuple(typing_records),
        analysis_units=tuple(analysis_units),
        analysis_groups=tuple(analysis_groups),
        analysis_sets=tuple(analysis_sets),
    )
