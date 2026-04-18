from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.models import (
    AnalysisArtifact,
    CaveatNote,
    DatasetVersion,
    L3AnalysisPlan,
    L3AnalysisSet,
    L3AnalysisUnit,
    L3MaterialSnapshot,
    L3PassRun,
    L3Session,
    uuid_str,
)
from app.services.analysis import recommend_analysis, run_analysis
from app.services.layer3_session_entry import (
    SESSION_STATUS_COMPLETED,
    SESSION_STATUS_COMPLETED_WITH_WARNINGS,
    SESSION_STATUS_FAILED,
)
from app.services.layer3_typing_entry import MODALITY_QUANTITATIVE, SET_TYPE_SINGLE_ITEM

SESSION_STATUS_ACTIVE_PLANNING = "active_planning"
SESSION_STATUS_ACTIVE_EXECUTION = "active_execution"

PLAN_STATUS_FORMED = "formed"

PASS_TYPE_SINGLE_ITEM = "single_item"
ENGINE_FAMILY_WRAPPED_QUANTITATIVE_ANALYSIS = "wrapped_quantitative_analysis"

PASS_STATUS_PLANNED = "planned"
PASS_STATUS_RUNNING = "running"
PASS_STATUS_COMPLETED = "completed"
PASS_STATUS_COMPLETED_WITH_WARNINGS = "completed_with_warnings"
PASS_STATUS_FAILED = "failed"

SOURCE_GATE_PASS_FREEZE = "06_GATEC_PASS_FREEZE"
PLAN_VERSION = "gatec_pass_entry_v1"
PASS_SCOPE_QUANT_SINGLE_ITEM = "quantitative_single_item_dataset_version"
SUPPORTED_WRAPPED_QUANTITATIVE_METHODS = frozenset(
    {
        "cross_correlation",
        "decomposition",
        "structural_break",
    }
)

FINALIZED_PASS_ENTRY_SESSION_STATUSES = frozenset(
    {
        SESSION_STATUS_COMPLETED,
        SESSION_STATUS_COMPLETED_WITH_WARNINGS,
    }
)


class Layer3PassEntryError(ValueError):
    pass


@dataclass(frozen=True)
class _AdmittedSetCandidate:
    analysis_set: L3AnalysisSet
    analysis_unit: L3AnalysisUnit
    snapshot: L3MaterialSnapshot
    dataset_version_id: str
    selected_method_name: str


@dataclass(frozen=True)
class Layer3PassEntryResult:
    analysis_plan: L3AnalysisPlan
    pass_runs: tuple[L3PassRun, ...]


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _utc_isoformat(value: datetime | None) -> str | None:
    if value is None:
        return None
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    else:
        value = value.astimezone(timezone.utc)
    return value.isoformat()


def _stable_json_bytes(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def _json_clone(value: Any) -> Any:
    return json.loads(_stable_json_bytes(value).decode("utf-8"))


def _layer3_artifact_dir() -> Path:
    path = Path(settings.artifact_storage_dir) / "layer3"
    path.mkdir(parents=True, exist_ok=True)
    return path


def _load_session_or_raise(db: Session, *, session_id: str) -> L3Session:
    session = db.get(L3Session, session_id)
    if session is None:
        raise Layer3PassEntryError(f"Layer 3 session '{session_id}' was not found")
    if session.status not in FINALIZED_PASS_ENTRY_SESSION_STATUSES or session.completed_at is None:
        raise Layer3PassEntryError(
            f"Layer 3 session '{session_id}' must be finalized before Gate C pass entry"
        )
    return session


def _ensure_session_not_yet_passed(db: Session, *, session_id: str) -> None:
    if db.query(L3AnalysisPlan).filter(L3AnalysisPlan.session_id == session_id).first() is not None:
        raise Layer3PassEntryError(f"Layer 3 session '{session_id}' already has analysis plans")
    if db.query(L3PassRun).filter(L3PassRun.session_id == session_id).first() is not None:
        raise Layer3PassEntryError(f"Layer 3 session '{session_id}' already has pass runs")


def _load_sets_units_and_snapshots(
    db: Session,
    *,
    session_id: str,
) -> tuple[list[L3AnalysisSet], dict[str, L3AnalysisUnit], dict[str, L3MaterialSnapshot]]:
    analysis_sets = (
        db.query(L3AnalysisSet)
        .filter(L3AnalysisSet.session_id == session_id)
        .order_by(L3AnalysisSet.analysis_set_id.asc())
        .all()
    )
    if not analysis_sets:
        raise Layer3PassEntryError(f"Layer 3 session '{session_id}' has no analysis sets for Gate C pass entry")

    analysis_units = (
        db.query(L3AnalysisUnit)
        .filter(L3AnalysisUnit.session_id == session_id)
        .order_by(L3AnalysisUnit.analysis_unit_id.asc())
        .all()
    )
    material_snapshots = (
        db.query(L3MaterialSnapshot)
        .filter(L3MaterialSnapshot.session_id == session_id)
        .order_by(L3MaterialSnapshot.material_snapshot_id.asc())
        .all()
    )
    return (
        analysis_sets,
        {unit.analysis_unit_id: unit for unit in analysis_units},
        {snapshot.material_snapshot_id: snapshot for snapshot in material_snapshots},
    )


def _exclusion_entry(analysis_set: L3AnalysisSet, *, reason_code: str, analysis_modality: str | None) -> dict[str, Any]:
    return {
        "analysis_set_id": analysis_set.analysis_set_id,
        "reason_code": reason_code,
        "analysis_modality": analysis_modality,
        "set_type": analysis_set.set_type,
    }


def _choose_method_name_or_raise(db: Session, *, dataset_version_id: str) -> str:
    recommendation = recommend_analysis(db, dataset_version_id, goal_type=None)
    sequence = recommendation.get("recommended_sequence") or []
    if not sequence:
        raise Layer3PassEntryError(
            f"Dataset version '{dataset_version_id}' has no recommended quantitative method for Gate C pass entry"
        )
    selected = str(sequence[0]).strip()
    if not selected:
        raise Layer3PassEntryError(
            f"Dataset version '{dataset_version_id}' yielded an empty quantitative method recommendation"
        )
    if selected not in SUPPORTED_WRAPPED_QUANTITATIVE_METHODS:
        raise Layer3PassEntryError(
            f"Dataset version '{dataset_version_id}' recommended unsupported Gate C method '{selected}'"
        )
    return selected


def _classify_sets(
    db: Session,
    *,
    analysis_sets: list[L3AnalysisSet],
    unit_by_id: dict[str, L3AnalysisUnit],
    snapshot_by_id: dict[str, L3MaterialSnapshot],
) -> tuple[list[_AdmittedSetCandidate], list[dict[str, Any]]]:
    admitted: list[_AdmittedSetCandidate] = []
    excluded: list[dict[str, Any]] = []

    for analysis_set in analysis_sets:
        analysis_unit_ids = list(analysis_set.analysis_unit_ids_json or [])
        analysis_modality = analysis_set.formation_basis_json.get("analysis_modality")
        if analysis_set.set_type != SET_TYPE_SINGLE_ITEM:
            excluded.append(
                _exclusion_entry(
                    analysis_set,
                    reason_code="set_type_not_admitted",
                    analysis_modality=analysis_modality,
                )
            )
            continue
        if len(analysis_unit_ids) != 1:
            excluded.append(
                _exclusion_entry(
                    analysis_set,
                    reason_code="analysis_unit_count_not_single_item",
                    analysis_modality=analysis_modality,
                )
            )
            continue
        analysis_unit = unit_by_id.get(analysis_unit_ids[0])
        if analysis_unit is None:
            raise Layer3PassEntryError(
                f"Layer 3 analysis set '{analysis_set.analysis_set_id}' references a missing analysis unit"
            )
        if analysis_unit.analysis_modality != MODALITY_QUANTITATIVE:
            excluded.append(
                _exclusion_entry(
                    analysis_set,
                    reason_code="analysis_modality_not_admitted",
                    analysis_modality=analysis_unit.analysis_modality,
                )
            )
            continue
        member_snapshot_ids = list(analysis_unit.member_snapshot_ids_json or [])
        if len(member_snapshot_ids) != 1:
            excluded.append(
                _exclusion_entry(
                    analysis_set,
                    reason_code="analysis_unit_not_single_snapshot",
                    analysis_modality=analysis_unit.analysis_modality,
                )
            )
            continue
        snapshot = snapshot_by_id.get(member_snapshot_ids[0])
        if snapshot is None:
            raise Layer3PassEntryError(
                f"Layer 3 analysis unit '{analysis_unit.analysis_unit_id}' references a missing material snapshot"
            )
        if snapshot.source_shape != "dataset_version":
            excluded.append(
                _exclusion_entry(
                    analysis_set,
                    reason_code="source_shape_not_admitted",
                    analysis_modality=analysis_unit.analysis_modality,
                )
            )
            continue
        dataset_version_id = str(snapshot.source_identity_json.get("dataset_version_id") or "").strip()
        if not dataset_version_id:
            excluded.append(
                _exclusion_entry(
                    analysis_set,
                    reason_code="dataset_version_identity_missing",
                    analysis_modality=analysis_unit.analysis_modality,
                )
            )
            continue
        dataset_version = db.get(DatasetVersion, dataset_version_id)
        if dataset_version is None:
            excluded.append(
                _exclusion_entry(
                    analysis_set,
                    reason_code="dataset_version_missing",
                    analysis_modality=analysis_unit.analysis_modality,
                )
            )
            continue
        storage_ref = str(dataset_version.storage_ref or "").strip()
        if not storage_ref or not Path(storage_ref).exists():
            excluded.append(
                _exclusion_entry(
                    analysis_set,
                    reason_code="dataset_storage_missing",
                    analysis_modality=analysis_unit.analysis_modality,
                )
            )
            continue
        try:
            selected_method_name = _choose_method_name_or_raise(db, dataset_version_id=dataset_version_id)
        except Layer3PassEntryError:
            excluded.append(
                _exclusion_entry(
                    analysis_set,
                    reason_code="recommended_method_not_admitted",
                    analysis_modality=analysis_unit.analysis_modality,
                )
            )
            continue
        admitted.append(
            _AdmittedSetCandidate(
                analysis_set=analysis_set,
                analysis_unit=analysis_unit,
                snapshot=snapshot,
                dataset_version_id=dataset_version_id,
                selected_method_name=selected_method_name,
            )
        )

    return admitted, excluded


def _preserve_phase1a_loading_closure(session: L3Session) -> dict[str, Any]:
    summary = _json_clone(session.summary_json)
    summary.setdefault(
        "phase1a_loading_closure",
        {
            "status": session.status,
            "completed_at": _utc_isoformat(session.completed_at),
            "summary_json": _json_clone(session.summary_json),
        },
    )
    return summary


def _plan_payload(
    admitted: list[_AdmittedSetCandidate],
    excluded: list[dict[str, Any]],
) -> dict[str, Any]:
    return {
        "plan_version": PLAN_VERSION,
        "planned_passes_json": [
            {
                "analysis_set_id": candidate.analysis_set.analysis_set_id,
                "pass_type": PASS_TYPE_SINGLE_ITEM,
                "engine_family": ENGINE_FAMILY_WRAPPED_QUANTITATIVE_ANALYSIS,
                "dataset_version_id": candidate.dataset_version_id,
                "selected_method_name": candidate.selected_method_name,
            }
            for candidate in admitted
        ],
        "excluded_sets_json": _json_clone(excluded),
        "formation_reason": "quantitative_single_item_dataset_version_only",
        "source_gate": SOURCE_GATE_PASS_FREEZE,
    }


def _materialize_analysis_plan(
    db: Session,
    *,
    session_id: str,
    admitted: list[_AdmittedSetCandidate],
    excluded: list[dict[str, Any]],
) -> L3AnalysisPlan:
    analysis_plan = L3AnalysisPlan(
        analysis_plan_id=uuid_str(),
        session_id=session_id,
        analysis_set_ids_json=[candidate.analysis_set.analysis_set_id for candidate in admitted],
        status=PLAN_STATUS_FORMED,
        approved_by_operator=False,
        approved_at=None,
        plan_json=_plan_payload(admitted, excluded),
        created_at=_utcnow(),
    )
    db.add(analysis_plan)
    db.flush()
    return analysis_plan


def _initial_pass_summary(candidate: _AdmittedSetCandidate) -> dict[str, Any]:
    return {
        "dataset_version_id": candidate.dataset_version_id,
        "selected_method_name": candidate.selected_method_name,
        "analysis_set_id": candidate.analysis_set.analysis_set_id,
        "pass_scope": PASS_SCOPE_QUANT_SINGLE_ITEM,
        "source_snapshot_id": candidate.snapshot.material_snapshot_id,
        "source_snapshot_payload_ref": candidate.snapshot.payload_ref,
        "analysis_run_id": None,
    }


def _persist_output_manifest(*, pass_run_id: str, payload: dict[str, Any]) -> str:
    output_path = _layer3_artifact_dir() / f"l3_pass_run_{pass_run_id}.json"
    output_path.write_text(json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False), encoding="utf-8")
    return str(output_path)


def _has_analysis_warnings(db: Session, *, analysis_run_id: str) -> bool:
    return db.query(CaveatNote).filter(CaveatNote.analysis_run_id == analysis_run_id).count() > 0


def _execute_passes(
    db: Session,
    *,
    analysis_plan: L3AnalysisPlan,
    session_id: str,
    admitted: list[_AdmittedSetCandidate],
) -> tuple[list[L3PassRun], list[str]]:
    pass_runs: list[L3PassRun] = []
    wrapped_analysis_run_ids: list[str] = []

    for candidate in admitted:
        pass_run = L3PassRun(
            pass_run_id=uuid_str(),
            session_id=session_id,
            analysis_plan_id=analysis_plan.analysis_plan_id,
            analysis_set_id=candidate.analysis_set.analysis_set_id,
            pass_type=PASS_TYPE_SINGLE_ITEM,
            engine_family=ENGINE_FAMILY_WRAPPED_QUANTITATIVE_ANALYSIS,
            status=PASS_STATUS_PLANNED,
            started_at=None,
            completed_at=None,
            input_payload_ref=candidate.snapshot.payload_ref,
            output_payload_ref=None,
            summary_json=_initial_pass_summary(candidate),
            created_at=_utcnow(),
        )
        db.add(pass_run)
        db.flush()

        pass_run.status = PASS_STATUS_RUNNING
        pass_run.started_at = _utcnow()
        db.flush()

        try:
            analysis_run = run_analysis(
                db,
                dataset_version_id=candidate.dataset_version_id,
                method_name=candidate.selected_method_name,
                goal_type=None,
                parameters={},
                annotation_window_id=None,
            )
        except Exception as exc:
            pass_run.status = PASS_STATUS_FAILED
            pass_run.completed_at = _utcnow()
            pass_run.summary_json = {
                **_json_clone(pass_run.summary_json),
                "error": str(exc),
            }
            db.flush()
            raise Layer3PassEntryError(
                f"Gate C pass entry failed for analysis set '{candidate.analysis_set.analysis_set_id}': {exc}"
            ) from exc

        artifacts = (
            db.query(AnalysisArtifact)
            .filter(AnalysisArtifact.analysis_run_id == analysis_run.analysis_run_id)
            .order_by(AnalysisArtifact.created_at.asc(), AnalysisArtifact.artifact_id.asc())
            .all()
        )
        output_manifest_ref = _persist_output_manifest(
            pass_run_id=pass_run.pass_run_id,
            payload={
                "analysis_run_id": analysis_run.analysis_run_id,
                "analysis_set_id": candidate.analysis_set.analysis_set_id,
                "dataset_version_id": candidate.dataset_version_id,
                "selected_method_name": candidate.selected_method_name,
                "artifact_refs_json": [artifact.storage_ref for artifact in artifacts],
                "artifact_types_json": [artifact.artifact_type for artifact in artifacts],
            },
        )
        has_warnings = _has_analysis_warnings(db, analysis_run_id=analysis_run.analysis_run_id)
        pass_run.status = PASS_STATUS_COMPLETED_WITH_WARNINGS if has_warnings else PASS_STATUS_COMPLETED
        pass_run.completed_at = _utcnow()
        pass_run.output_payload_ref = output_manifest_ref
        pass_run.summary_json = {
            **_json_clone(pass_run.summary_json),
            "analysis_run_id": analysis_run.analysis_run_id,
            "artifact_refs_json": [artifact.storage_ref for artifact in artifacts],
            "pass_status_from_analysis": analysis_run.status,
        }
        db.flush()

        pass_runs.append(pass_run)
        wrapped_analysis_run_ids.append(analysis_run.analysis_run_id)

    return pass_runs, wrapped_analysis_run_ids


def _final_session_status(
    *,
    original_status: str,
    excluded_set_count: int,
    pass_runs: list[L3PassRun],
) -> str:
    if any(pass_run.status == PASS_STATUS_FAILED for pass_run in pass_runs):
        return SESSION_STATUS_FAILED
    if original_status == SESSION_STATUS_COMPLETED_WITH_WARNINGS:
        return SESSION_STATUS_COMPLETED_WITH_WARNINGS
    if excluded_set_count > 0 or any(pass_run.status == PASS_STATUS_COMPLETED_WITH_WARNINGS for pass_run in pass_runs):
        return SESSION_STATUS_COMPLETED_WITH_WARNINGS
    return SESSION_STATUS_COMPLETED


def _materialize_failed_execution_state(
    db: Session,
    *,
    session: L3Session,
    analysis_plan: L3AnalysisPlan,
    excluded: list[dict[str, Any]],
    error_message: str,
) -> None:
    pass_runs = (
        db.query(L3PassRun)
        .filter(L3PassRun.analysis_plan_id == analysis_plan.analysis_plan_id)
        .order_by(L3PassRun.created_at.asc(), L3PassRun.pass_run_id.asc())
        .all()
    )
    wrapped_analysis_run_ids = [
        analysis_run_id
        for analysis_run_id in (str((pass_run.summary_json or {}).get("analysis_run_id") or "").strip() for pass_run in pass_runs)
        if analysis_run_id
    ]
    session.status = SESSION_STATUS_FAILED
    session.completed_at = _utcnow()
    session.summary_json = {
        **_json_clone(session.summary_json),
        "pass_entry": {
            "analysis_plan_id": analysis_plan.analysis_plan_id,
            "pass_run_ids_json": [pass_run.pass_run_id for pass_run in pass_runs],
            "admitted_set_count": len(analysis_plan.analysis_set_ids_json or []),
            "excluded_set_count": len(excluded),
            "excluded_sets_json": _json_clone(excluded),
            "wrapped_analysis_run_ids_json": wrapped_analysis_run_ids,
            "source_gate": SOURCE_GATE_PASS_FREEZE,
            "failure_reason": error_message,
        },
    }
    db.flush()


def materialize_pass_entry(db: Session, *, session_id: str) -> Layer3PassEntryResult:
    session = _load_session_or_raise(db, session_id=session_id)
    _ensure_session_not_yet_passed(db, session_id=session_id)
    analysis_sets, unit_by_id, snapshot_by_id = _load_sets_units_and_snapshots(db, session_id=session_id)
    admitted, excluded = _classify_sets(
        db,
        analysis_sets=analysis_sets,
        unit_by_id=unit_by_id,
        snapshot_by_id=snapshot_by_id,
    )
    if not admitted:
        raise Layer3PassEntryError(
            f"Layer 3 session '{session_id}' has no admissible analysis sets for Gate C pass entry"
        )

    original_status = session.status
    summary = _preserve_phase1a_loading_closure(session)
    session.status = SESSION_STATUS_ACTIVE_PLANNING
    session.completed_at = None
    session.summary_json = summary
    db.flush()

    analysis_plan = _materialize_analysis_plan(
        db,
        session_id=session_id,
        admitted=admitted,
        excluded=excluded,
    )

    session.status = SESSION_STATUS_ACTIVE_EXECUTION
    db.flush()

    try:
        pass_runs, wrapped_analysis_run_ids = _execute_passes(
            db,
            analysis_plan=analysis_plan,
            session_id=session_id,
            admitted=admitted,
        )
    except Layer3PassEntryError as exc:
        _materialize_failed_execution_state(
            db,
            session=session,
            analysis_plan=analysis_plan,
            excluded=excluded,
            error_message=str(exc),
        )
        db.commit()
        raise

    session.status = _final_session_status(
        original_status=original_status,
        excluded_set_count=len(excluded),
        pass_runs=pass_runs,
    )
    session.completed_at = _utcnow()
    session.summary_json = {
        **_json_clone(session.summary_json),
        "pass_entry": {
            "analysis_plan_id": analysis_plan.analysis_plan_id,
            "pass_run_ids_json": [pass_run.pass_run_id for pass_run in pass_runs],
            "admitted_set_count": len(admitted),
            "excluded_set_count": len(excluded),
            "excluded_sets_json": _json_clone(excluded),
            "wrapped_analysis_run_ids_json": wrapped_analysis_run_ids,
            "source_gate": SOURCE_GATE_PASS_FREEZE,
        },
    }
    db.flush()

    return Layer3PassEntryResult(
        analysis_plan=analysis_plan,
        pass_runs=tuple(pass_runs),
    )
