from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from app.models.models import (
    L3AnalysisGroup,
    L3AnalysisPlan,
    L3AnalysisSet,
    L3AnalysisUnit,
    L3MaterialSnapshot,
    L3PassRun,
    L3TypingRecord,
)
from app.services.layer3_plan_flow_state import latest_analysis_plan
from app.services.layer3_typing_entry import SUPPORTED_TYPING_RULES
from app.services.layer3_utils import json_clone


SUBLAYER_VISUALIZATION_STATE_SCHEMA_ID = "layer3.sublayer_visualization_state.v1"


def snapshot_projection(
    snapshot: L3MaterialSnapshot,
) -> tuple[dict[str, Any] | None, dict[str, Any] | None]:
    rule = SUPPORTED_TYPING_RULES.get(snapshot.source_shape)
    if rule is None:
        return None, {
            "material_snapshot_id": snapshot.material_snapshot_id,
            "owner_service_source_shape": snapshot.source_shape,
            "reason": "unsupported_typing_shape",
        }
    return {
        "typing_record_id": None,
        "material_snapshot_id": snapshot.material_snapshot_id,
        "owner_service_source_shape": snapshot.source_shape,
        "planning_shape_family": rule.planning_shape_family,
        "candidate_modalities": list(rule.candidate_modalities),
        "chosen_modality": rule.chosen_modality,
        "confidence": rule.confidence,
        "authoritative": False,
    }, None


def serialize_typing_record(record: L3TypingRecord) -> dict[str, Any]:
    basis = record.typing_basis_json or {}
    return {
        "typing_record_id": record.typing_record_id,
        "material_snapshot_id": record.material_snapshot_id,
        "owner_service_source_shape": basis.get("source_shape"),
        "planning_shape_family": basis.get("planning_shape_family"),
        "candidate_modalities": list(record.candidate_modalities_json or []),
        "chosen_modality": record.chosen_modality,
        "confidence": record.confidence,
        "authoritative": True,
    }


def serialize_analysis_unit(unit: L3AnalysisUnit) -> dict[str, Any]:
    return {
        "analysis_unit_id": unit.analysis_unit_id,
        "unit_kind": unit.unit_kind,
        "analysis_modality": unit.analysis_modality,
        "member_snapshot_ids": list(unit.member_snapshot_ids_json or []),
        "typing_record_ids": list(unit.typing_record_ids_json or []),
        "must_remain_intact": unit.must_remain_intact,
        "authoritative": True,
    }


def serialize_analysis_group(group: L3AnalysisGroup) -> dict[str, Any]:
    return {
        "analysis_group_id": group.analysis_group_id,
        "analysis_modality": group.analysis_modality,
        "analysis_unit_ids": list(group.analysis_unit_ids_json or []),
        "status": group.status,
        "typing_basis": group.typing_basis_json or {},
    }


def serialize_analysis_set(analysis_set: L3AnalysisSet) -> dict[str, Any]:
    return {
        "analysis_set_id": analysis_set.analysis_set_id,
        "analysis_group_ids": list(analysis_set.analysis_group_ids_json or []),
        "analysis_unit_ids": list(analysis_set.analysis_unit_ids_json or []),
        "set_type": analysis_set.set_type,
        "formation_basis": analysis_set.formation_basis_json or {},
    }


def serialize_sublayer_material_object(snapshot: L3MaterialSnapshot) -> dict[str, Any]:
    source_identity = snapshot.source_identity_json or {}
    load_summary = snapshot.load_summary_json or {}
    return {
        "material_snapshot_id": snapshot.material_snapshot_id,
        "source_shape": snapshot.source_shape,
        "source_plane": snapshot.source_plane,
        "source_identity": json_clone(source_identity),
        "load_summary": json_clone(load_summary),
        "payload_hash": snapshot.payload_hash,
        "co_retrieval_group_id": snapshot.co_retrieval_group_id,
        "state": "loaded",
    }


def serialize_sublayer_typing_record(
    record: L3TypingRecord,
    *,
    snapshot_by_id: dict[str, L3MaterialSnapshot],
) -> dict[str, Any]:
    serialized = serialize_typing_record(record)
    snapshot = snapshot_by_id.get(record.material_snapshot_id)
    if snapshot is not None:
        serialized["owner_service_source_shape"] = serialized.get("owner_service_source_shape") or snapshot.source_shape
        serialized["source_identity"] = json_clone(snapshot.source_identity_json or {})
        serialized["payload_hash"] = snapshot.payload_hash
    return serialized


def serialize_sublayer_analysis_set(
    analysis_set: L3AnalysisSet,
    *,
    unit_by_id: dict[str, L3AnalysisUnit],
) -> dict[str, Any]:
    serialized = serialize_analysis_set(analysis_set)
    units = [unit_by_id[unit_id] for unit_id in serialized["analysis_unit_ids"] if unit_id in unit_by_id]
    formation_basis = serialized["formation_basis"]
    member_snapshot_ids: list[str] = []
    for unit in units:
        member_snapshot_ids.extend(str(item) for item in (unit.member_snapshot_ids_json or []))
    analysis_modality = formation_basis.get("analysis_modality") or (units[0].analysis_modality if units else None)
    serialized.update(
        {
            "analysis_modality": analysis_modality,
            "member_snapshot_ids": sorted(set(member_snapshot_ids)),
            "unit_count": len(units),
            "state": "formed",
        }
    )
    return serialized


def serialize_sublayer_pass_run(pass_run: L3PassRun) -> dict[str, Any]:
    summary = pass_run.summary_json or {}
    return {
        "pass_run_id": pass_run.pass_run_id,
        "analysis_plan_id": pass_run.analysis_plan_id,
        "analysis_set_id": pass_run.analysis_set_id,
        "pass_type": pass_run.pass_type,
        "engine_family": pass_run.engine_family,
        "status": pass_run.status,
        "input_payload_available": bool(pass_run.input_payload_ref),
        "output_payload_available": bool(pass_run.output_payload_ref),
        "analysis_run_id": summary.get("analysis_run_id"),
        "selected_method_name": summary.get("selected_method_name"),
        "pass_scope": summary.get("pass_scope"),
    }


def serialize_sublayer_latest_plan(analysis_plan: L3AnalysisPlan | None) -> dict[str, Any] | None:
    if analysis_plan is None:
        return None
    plan_json = analysis_plan.plan_json or {}
    return {
        "analysis_plan_id": analysis_plan.analysis_plan_id,
        "plan_status": analysis_plan.status,
        "approved": bool(analysis_plan.approved_by_operator),
        "approved_by_operator": bool(analysis_plan.approved_by_operator),
        "approval_only": bool(plan_json.get("approval_only")),
        "execution_started": bool(plan_json.get("execution_started")),
        "approved_sets": json_clone(plan_json.get("approved_sets_json") or []),
        "admitted_sets": json_clone(plan_json.get("admitted_sets") or plan_json.get("admitted_sets_json") or []),
        "excluded_sets": json_clone(plan_json.get("excluded_sets_json") or []),
        "planned_passes": json_clone(plan_json.get("planned_passes_json") or []),
        "source_preview_id": plan_json.get("source_preview_id"),
        "source_preview_hash": plan_json.get("source_preview_hash"),
    }


def session_sublayer_visualization_state(db: Session, *, session_id: str) -> dict[str, Any]:
    snapshots = (
        db.query(L3MaterialSnapshot)
        .filter(L3MaterialSnapshot.session_id == session_id)
        .order_by(L3MaterialSnapshot.material_snapshot_id.asc())
        .all()
    )
    typing_records = (
        db.query(L3TypingRecord)
        .filter(L3TypingRecord.session_id == session_id)
        .order_by(L3TypingRecord.typing_record_id.asc())
        .all()
    )
    analysis_units = (
        db.query(L3AnalysisUnit)
        .filter(L3AnalysisUnit.session_id == session_id)
        .order_by(L3AnalysisUnit.analysis_unit_id.asc())
        .all()
    )
    analysis_sets = (
        db.query(L3AnalysisSet)
        .filter(L3AnalysisSet.session_id == session_id)
        .order_by(L3AnalysisSet.analysis_set_id.asc())
        .all()
    )
    pass_runs = (
        db.query(L3PassRun)
        .filter(L3PassRun.session_id == session_id)
        .order_by(L3PassRun.pass_run_id.asc())
        .all()
    )
    snapshot_by_id = {snapshot.material_snapshot_id: snapshot for snapshot in snapshots}
    unit_by_id = {unit.analysis_unit_id: unit for unit in analysis_units}
    return {
        "schema_id": SUBLAYER_VISUALIZATION_STATE_SCHEMA_ID,
        "authority_source": "read_only_persisted_layer3_rows",
        "material_objects": [serialize_sublayer_material_object(snapshot) for snapshot in snapshots],
        "typing_records": [
            serialize_sublayer_typing_record(record, snapshot_by_id=snapshot_by_id)
            for record in typing_records
        ],
        "analysis_units": [serialize_analysis_unit(unit) for unit in analysis_units],
        "analysis_sets": [
            serialize_sublayer_analysis_set(analysis_set, unit_by_id=unit_by_id)
            for analysis_set in analysis_sets
        ],
        "pass_runs": [serialize_sublayer_pass_run(pass_run) for pass_run in pass_runs],
        "latest_plan": serialize_sublayer_latest_plan(latest_analysis_plan(db, session_id=session_id)),
        "no_side_effects": True,
    }
