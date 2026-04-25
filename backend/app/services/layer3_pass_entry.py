from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.models import (
    AnalysisArtifact,
    CaveatNote,
    Dataset,
    DatasetVersion,
    L3AnalysisPlan,
    L3AnalysisSet,
    L3AnalysisUnit,
    L3MaterialSnapshot,
    L3PassRun,
    L3Session,
    VariableDefinition,
    VariableProfile,
    uuid_str,
)
from app.services.analysis import recommend_analysis, run_analysis
from app.services.dataframe_io import load_version_dataframe, persist_dataframe_as_version_rows
from app.services.layer3_session_entry import (
    SESSION_STATUS_COMPLETED,
    SESSION_STATUS_COMPLETED_WITH_WARNINGS,
    SESSION_STATUS_FAILED,
)
from app.services.layer3_typing_entry import (
    MODALITY_QUANTITATIVE,
    SET_TYPE_ASSOCIATED_COHORT,
    SET_TYPE_SINGLE_ITEM,
)

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
SOURCE_GATE_COHORT_FREEZE = "07_GATEC_COHORT_FREEZE"
PLAN_VERSION = "gatec_pass_entry_v1"
PASS_SCOPE_QUANT_SINGLE_ITEM = "quantitative_single_item_dataset_version"
PASS_SCOPE_QUANT_ASSOCIATED_COHORT = "quantitative_associated_cohort_dataset_version"
PASS_TYPE_ASSOCIATED_COHORT = "associated_cohort"
COHORT_TIME_COLUMN = "observed_at"
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
class _PreparedCohortColumn:
    column_name: str
    analysis_unit_id: str
    material_snapshot_id: str
    dataset_version_id: str
    descriptor_id: str
    stationarity_hint: str | None
    seasonality_flag: bool | None

    def manifest_entry(self) -> dict[str, Any]:
        return {
            "column_name": self.column_name,
            "analysis_unit_id": self.analysis_unit_id,
            "material_snapshot_id": self.material_snapshot_id,
            "dataset_version_id": self.dataset_version_id,
            "descriptor_id": self.descriptor_id,
        }


@dataclass(frozen=True)
class _PreparedCohortCandidate:
    shaped_dataframe: pd.DataFrame
    source_dataset_version_ids: tuple[str, ...]
    columns: tuple[_PreparedCohortColumn, ...]
    frequency_hint: str | None


@dataclass(frozen=True)
class _AdmittedSetCandidate:
    analysis_set: L3AnalysisSet
    analysis_units: tuple[L3AnalysisUnit, ...]
    snapshots: tuple[L3MaterialSnapshot, ...]
    pass_type: str
    pass_scope: str
    source_gate: str
    selected_method_name: str
    dataset_version_id: str | None = None
    input_payload_ref: str | None = None
    prepared_cohort: _PreparedCohortCandidate | None = None


@dataclass(frozen=True)
class Layer3PassEntryResult:
    analysis_plan: L3AnalysisPlan
    pass_runs: tuple[L3PassRun, ...]


@dataclass(frozen=True)
class Layer3PassEntryPreviewResult:
    session_id: str
    admitted_sets: tuple[dict[str, Any], ...]
    excluded_sets: tuple[dict[str, Any], ...]
    planned_passes: tuple[dict[str, Any], ...]
    warnings: tuple[dict[str, Any], ...]
    owner_service_basis: dict[str, Any]
    owner_plan_payload: dict[str, Any]


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


def _unit_column_name(analysis_unit_id: str) -> str:
    return f"analysis_unit_{analysis_unit_id.replace('-', '_')}"


def _choose_cohort_method_name_or_raise(*, shaped_dataframe: pd.DataFrame) -> str:
    numeric_columns = [column for column in shaped_dataframe.columns if column != COHORT_TIME_COLUMN]
    if COHORT_TIME_COLUMN in shaped_dataframe.columns and len(numeric_columns) >= 2:
        return "cross_correlation"
    raise Layer3PassEntryError("shaped cohort recommended unsupported Gate C method 'descriptive_summary'")


def _load_source_profile(
    db: Session,
    *,
    dataset_version_id: str,
    variable_name: str,
) -> VariableProfile | None:
    return (
        db.query(VariableProfile)
        .join(VariableDefinition, VariableProfile.variable_id == VariableDefinition.variable_id)
        .filter(VariableProfile.dataset_version_id == dataset_version_id)
        .filter(VariableDefinition.variable_name == variable_name)
        .first()
    )


def _prepare_cohort_candidate(
    db: Session,
    *,
    analysis_set: L3AnalysisSet,
    analysis_unit_ids: list[str],
    analysis_modality: str | None,
    unit_by_id: dict[str, L3AnalysisUnit],
    snapshot_by_id: dict[str, L3MaterialSnapshot],
) -> tuple[_PreparedCohortCandidate | None, str | None]:
    if analysis_modality != MODALITY_QUANTITATIVE:
        return None, "cohort_not_quantitative"
    if len(analysis_unit_ids) < 2:
        return None, "cohort_cardinality_not_admitted"

    prepared_sources: list[tuple[str, str, pd.DataFrame, _PreparedCohortColumn]] = []
    frequency_hints: list[str] = []

    for analysis_unit_id in analysis_unit_ids:
        analysis_unit = unit_by_id.get(analysis_unit_id)
        if analysis_unit is None:
            raise Layer3PassEntryError(
                f"Layer 3 analysis set '{analysis_set.analysis_set_id}' references a missing analysis unit"
            )
        if analysis_unit.analysis_modality != MODALITY_QUANTITATIVE:
            return None, "cohort_not_quantitative"

        member_snapshot_ids = list(analysis_unit.member_snapshot_ids_json or [])
        if len(member_snapshot_ids) != 1:
            return None, "cohort_member_not_single_snapshot"
        snapshot = snapshot_by_id.get(member_snapshot_ids[0])
        if snapshot is None:
            raise Layer3PassEntryError(
                f"Layer 3 analysis unit '{analysis_unit.analysis_unit_id}' references a missing material snapshot"
            )
        if snapshot.source_shape != "dataset_version":
            return None, "cohort_source_shape_not_dataset_version"

        dataset_version_id = str(snapshot.source_identity_json.get("dataset_version_id") or "").strip()
        if not dataset_version_id:
            return None, "dataset_version_identity_missing"
        dataset_version = db.get(DatasetVersion, dataset_version_id)
        if dataset_version is None:
            return None, "dataset_version_missing"
        if not str(dataset_version.storage_ref or "").strip() or not Path(str(dataset_version.storage_ref)).exists():
            return None, "dataset_storage_missing"

        dataset = db.get(Dataset, dataset_version.dataset_id)
        if dataset is None or not str(dataset.time_column or "").strip():
            return None, "cohort_measure_signature_not_admitted"

        variables = (
            db.query(VariableDefinition)
            .filter(VariableDefinition.dataset_version_id == dataset_version_id)
            .order_by(VariableDefinition.ordinal_position.asc())
            .all()
        )
        measure_variables = [variable for variable in variables if variable.is_numeric and not variable.is_time_index]
        if len(measure_variables) != 1:
            return None, "cohort_measure_signature_not_admitted"

        measure_variable = measure_variables[0]
        source_frame = load_version_dataframe(db, dataset_version_id)
        if dataset.time_column not in source_frame.columns or measure_variable.variable_name not in source_frame.columns:
            return None, "cohort_measure_signature_not_admitted"

        series_column = _unit_column_name(analysis_unit.analysis_unit_id)
        aligned_frame = pd.DataFrame(
            {
                COHORT_TIME_COLUMN: pd.to_datetime(source_frame[dataset.time_column], errors="coerce", utc=True),
                series_column: pd.to_numeric(source_frame[measure_variable.variable_name], errors="coerce"),
            }
        ).dropna()
        if aligned_frame.empty or aligned_frame[COHORT_TIME_COLUMN].duplicated().any():
            return None, "cohort_measure_signature_not_admitted"
        aligned_frame = aligned_frame.sort_values(COHORT_TIME_COLUMN).reset_index(drop=True)

        source_profile = _load_source_profile(
            db,
            dataset_version_id=dataset_version_id,
            variable_name=measure_variable.variable_name,
        )
        prepared_sources.append(
            (
                dataset_version_id,
                analysis_unit.analysis_unit_id,
                aligned_frame,
                _PreparedCohortColumn(
                    column_name=series_column,
                    analysis_unit_id=analysis_unit.analysis_unit_id,
                    material_snapshot_id=snapshot.material_snapshot_id,
                    dataset_version_id=dataset_version_id,
                    descriptor_id=snapshot.descriptor_id,
                    stationarity_hint=source_profile.stationarity_hint if source_profile is not None else None,
                    seasonality_flag=source_profile.seasonality_flag if source_profile is not None else None,
                ),
            )
        )
        if dataset.frequency_hint:
            frequency_hints.append(dataset.frequency_hint)

    prepared_sources.sort(key=lambda item: (item[0], item[1]))
    source_frames = [item[2] for item in prepared_sources]
    source_dataset_version_ids = [item[0] for item in prepared_sources]
    prepared_columns = [item[3] for item in prepared_sources]

    shaped_dataframe = source_frames[0]
    for source_frame in source_frames[1:]:
        shaped_dataframe = shaped_dataframe.merge(source_frame, on=COHORT_TIME_COLUMN, how="inner")
    if shaped_dataframe.empty:
        return None, "cohort_time_alignment_empty"

    try:
        _choose_cohort_method_name_or_raise(shaped_dataframe=shaped_dataframe)
    except Layer3PassEntryError:
        return None, "cohort_recommended_method_not_admitted"

    distinct_hints = {hint for hint in frequency_hints if hint}
    frequency_hint = next(iter(distinct_hints)) if len(distinct_hints) == 1 else None
    return (
        _PreparedCohortCandidate(
            shaped_dataframe=shaped_dataframe,
            source_dataset_version_ids=tuple(source_dataset_version_ids),
            columns=tuple(prepared_columns),
            frequency_hint=frequency_hint,
        ),
        None,
    )


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
        if analysis_set.set_type == SET_TYPE_ASSOCIATED_COHORT:
            prepared_cohort, exclusion_reason = _prepare_cohort_candidate(
                db,
                analysis_set=analysis_set,
                analysis_unit_ids=analysis_unit_ids,
                analysis_modality=analysis_modality,
                unit_by_id=unit_by_id,
                snapshot_by_id=snapshot_by_id,
            )
            if exclusion_reason is not None:
                excluded.append(
                    _exclusion_entry(
                        analysis_set,
                        reason_code=exclusion_reason,
                        analysis_modality=analysis_modality,
                    )
                )
                continue
            assert prepared_cohort is not None
            admitted.append(
                _AdmittedSetCandidate(
                    analysis_set=analysis_set,
                    analysis_units=tuple(unit_by_id[analysis_unit_id] for analysis_unit_id in analysis_unit_ids),
                    snapshots=tuple(
                        snapshot_by_id[unit_by_id[analysis_unit_id].member_snapshot_ids_json[0]]
                        for analysis_unit_id in analysis_unit_ids
                    ),
                    pass_type=PASS_TYPE_ASSOCIATED_COHORT,
                    pass_scope=PASS_SCOPE_QUANT_ASSOCIATED_COHORT,
                    source_gate=SOURCE_GATE_COHORT_FREEZE,
                    selected_method_name=_choose_cohort_method_name_or_raise(
                        shaped_dataframe=prepared_cohort.shaped_dataframe
                    ),
                    prepared_cohort=prepared_cohort,
                )
            )
            continue

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
                analysis_units=(analysis_unit,),
                snapshots=(snapshot,),
                pass_type=PASS_TYPE_SINGLE_ITEM,
                pass_scope=PASS_SCOPE_QUANT_SINGLE_ITEM,
                source_gate=SOURCE_GATE_PASS_FREEZE,
                selected_method_name=selected_method_name,
                dataset_version_id=dataset_version_id,
                input_payload_ref=snapshot.payload_ref,
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
                "set_type": candidate.analysis_set.set_type,
                "pass_type": candidate.pass_type,
                "pass_scope": candidate.pass_scope,
                "engine_family": ENGINE_FAMILY_WRAPPED_QUANTITATIVE_ANALYSIS,
                "selected_method_name": candidate.selected_method_name,
                "source_gate": candidate.source_gate,
                **(
                    {"dataset_version_id": candidate.dataset_version_id}
                    if candidate.dataset_version_id is not None
                    else {
                        "source_dataset_version_ids_json": list(
                            candidate.prepared_cohort.source_dataset_version_ids
                        )
                    }
                ),
            }
            for candidate in admitted
        ],
        "excluded_sets_json": _json_clone(excluded),
        "formation_reason": "quantitative_dataset_version_backed_gatec_only",
        "source_gate": SOURCE_GATE_COHORT_FREEZE
        if any(candidate.pass_type == PASS_TYPE_ASSOCIATED_COHORT for candidate in admitted)
        else SOURCE_GATE_PASS_FREEZE,
    }


def _candidate_source_summary(candidate: _AdmittedSetCandidate) -> dict[str, Any]:
    return {
        "source_classes": sorted({snapshot.source_shape for snapshot in candidate.snapshots}),
        "source_material_count": len(candidate.snapshots),
    }


def _preview_admitted_entry(candidate: _AdmittedSetCandidate) -> dict[str, Any]:
    return {
        "analysis_set_id": candidate.analysis_set.analysis_set_id,
        "analysis_unit_ids": [unit.analysis_unit_id for unit in candidate.analysis_units],
        "material_snapshot_ids": [snapshot.material_snapshot_id for snapshot in candidate.snapshots],
        "analysis_modality": candidate.analysis_set.formation_basis_json.get("analysis_modality"),
        "pass_type": candidate.pass_type,
        "pass_scope": candidate.pass_scope,
        "readiness": "admitted",
        "source_summary": _candidate_source_summary(candidate),
    }


def _preview_excluded_entry(
    excluded: dict[str, Any],
    *,
    analysis_set_by_id: dict[str, L3AnalysisSet],
    unit_by_id: dict[str, L3AnalysisUnit],
    snapshot_by_id: dict[str, L3MaterialSnapshot],
) -> dict[str, Any]:
    analysis_set_id = str(excluded.get("analysis_set_id") or "")
    analysis_set = analysis_set_by_id.get(analysis_set_id)
    analysis_unit_ids = list(analysis_set.analysis_unit_ids_json or []) if analysis_set is not None else []
    snapshot_ids: list[str] = []
    source_classes: set[str] = set()
    for analysis_unit_id in analysis_unit_ids:
        analysis_unit = unit_by_id.get(analysis_unit_id)
        if analysis_unit is None:
            continue
        for snapshot_id in list(analysis_unit.member_snapshot_ids_json or []):
            snapshot_ids.append(snapshot_id)
            snapshot = snapshot_by_id.get(snapshot_id)
            if snapshot is not None:
                source_classes.add(snapshot.source_shape)
    return {
        "analysis_set_id": analysis_set_id,
        "reason_code": excluded.get("reason_code"),
        "analysis_modality": excluded.get("analysis_modality"),
        "set_type": excluded.get("set_type"),
        "analysis_unit_ids": analysis_unit_ids,
        "material_snapshot_ids": snapshot_ids,
        "source_summary": {
            "source_classes": sorted(source_classes),
            "source_material_count": len(snapshot_ids),
        },
    }


def _preview_planned_pass(candidate: _AdmittedSetCandidate) -> dict[str, Any]:
    result = {
        "pass_type": candidate.pass_type,
        "pass_scope": candidate.pass_scope,
        "analysis_set_id": candidate.analysis_set.analysis_set_id,
        "method_family": "repo_supported_quantitative",
        "selected_method_name": candidate.selected_method_name,
        "execution_status": "not_started",
        "preview_only": True,
    }
    if candidate.dataset_version_id is not None:
        result["dataset_version_id"] = candidate.dataset_version_id
    if candidate.prepared_cohort is not None:
        result["source_dataset_version_ids"] = list(candidate.prepared_cohort.source_dataset_version_ids)
    return result


def preview_pass_entry(db: Session, *, session_id: str) -> Layer3PassEntryPreviewResult:
    """Return the Gate C pass-entry plan basis without materializing or executing it."""

    _load_session_or_raise(db, session_id=session_id)
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

    plan_payload = _plan_payload(admitted, excluded)
    analysis_set_by_id = {analysis_set.analysis_set_id: analysis_set for analysis_set in analysis_sets}
    warnings = []
    if excluded:
        warnings.append(
            {
                "reason_code": "partial_plan_preview",
                "message": "Some analysis sets are excluded by the current Gate C pass-entry rules.",
                "excluded_set_count": len(excluded),
            }
        )
    return Layer3PassEntryPreviewResult(
        session_id=session_id,
        admitted_sets=tuple(_preview_admitted_entry(candidate) for candidate in admitted),
        excluded_sets=tuple(
            _preview_excluded_entry(
                item,
                analysis_set_by_id=analysis_set_by_id,
                unit_by_id=unit_by_id,
                snapshot_by_id=snapshot_by_id,
            )
            for item in excluded
        ),
        planned_passes=tuple(_preview_planned_pass(candidate) for candidate in admitted),
        warnings=tuple(warnings),
        owner_service_basis={
            "service": "backend/app/services/layer3_pass_entry.py",
            "mode": "read_only_preview",
            "source_gate": plan_payload["source_gate"],
            "owner_plan_version": PLAN_VERSION,
        },
        owner_plan_payload=_json_clone(plan_payload),
    )


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
    summary = {
        "dataset_version_id": candidate.dataset_version_id,
        "selected_method_name": candidate.selected_method_name,
        "analysis_set_id": candidate.analysis_set.analysis_set_id,
        "pass_scope": candidate.pass_scope,
        "analysis_run_id": None,
    }
    if candidate.pass_type == PASS_TYPE_SINGLE_ITEM:
        snapshot = candidate.snapshots[0]
        summary["source_snapshot_id"] = snapshot.material_snapshot_id
        summary["source_snapshot_payload_ref"] = snapshot.payload_ref
    else:
        assert candidate.prepared_cohort is not None
        summary["derived_dataset_version_id"] = None
        summary["source_dataset_version_ids_json"] = list(candidate.prepared_cohort.source_dataset_version_ids)
        summary["column_map_json"] = [column.manifest_entry() for column in candidate.prepared_cohort.columns]
    return summary


def _persist_input_manifest(*, pass_run_id: str, payload: dict[str, Any]) -> str:
    input_path = _layer3_artifact_dir() / f"l3_pass_input_{pass_run_id}.json"
    input_path.write_text(json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False), encoding="utf-8")
    return str(input_path)


def _persist_cohort_dataset_version(
    db: Session,
    *,
    session_id: str,
    analysis_set_id: str,
    pass_run_id: str,
    prepared_cohort: _PreparedCohortCandidate,
) -> tuple[str, str]:
    dataset = Dataset(
        name=f"L3 cohort {analysis_set_id}",
        description="Derived Gate C quantitative associated cohort input",
        frequency_hint=prepared_cohort.frequency_hint,
        time_column=COHORT_TIME_COLUMN,
    )
    db.add(dataset)
    db.flush()

    version = DatasetVersion(
        dataset_id=dataset.dataset_id,
        version_label="l3_cohort_v1",
        version_type="derived",
        status="ready",
        notes=f"layer3_gatec_cohort; session_id={session_id}; analysis_set_id={analysis_set_id}",
    )
    db.add(version)
    db.flush()

    time_variable = VariableDefinition(
        dataset_version_id=version.dataset_version_id,
        variable_name=COHORT_TIME_COLUMN,
        dtype="datetime64[ns]",
        role="time_index",
        is_numeric=False,
        is_time_index=True,
        ordinal_position=0,
    )
    db.add(time_variable)
    db.flush()

    for ordinal_position, prepared_column in enumerate(prepared_cohort.columns, start=1):
        variable = VariableDefinition(
            dataset_version_id=version.dataset_version_id,
            variable_name=prepared_column.column_name,
            dtype="float64",
            role="measure",
            is_numeric=True,
            is_time_index=False,
            ordinal_position=ordinal_position,
        )
        db.add(variable)
        db.flush()
        db.add(
            VariableProfile(
                dataset_version_id=version.dataset_version_id,
                variable_id=variable.variable_id,
                seasonality_flag=prepared_column.seasonality_flag,
                stationarity_hint=prepared_column.stationarity_hint,
                summary_json={
                    "derived_from": "layer3_associated_cohort",
                    "analysis_unit_id": prepared_column.analysis_unit_id,
                    "material_snapshot_id": prepared_column.material_snapshot_id,
                    "dataset_version_id": prepared_column.dataset_version_id,
                    "descriptor_id": prepared_column.descriptor_id,
                },
            )
        )

    persist_dataframe_as_version_rows(
        db,
        version,
        prepared_cohort.shaped_dataframe,
        COHORT_TIME_COLUMN,
    )
    manifest_ref = _persist_input_manifest(
        pass_run_id=pass_run_id,
        payload={
            "analysis_set_id": analysis_set_id,
            "derived_dataset_version_id": version.dataset_version_id,
            "source_dataset_version_ids_json": list(prepared_cohort.source_dataset_version_ids),
            "column_map_json": [prepared_column.manifest_entry() for prepared_column in prepared_cohort.columns],
            "time_column": COHORT_TIME_COLUMN,
            "row_count": int(len(prepared_cohort.shaped_dataframe)),
            "source_gate": SOURCE_GATE_COHORT_FREEZE,
        },
    )
    return version.dataset_version_id, manifest_ref


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
        pass_run_id = uuid_str()
        dataset_version_id = candidate.dataset_version_id
        input_payload_ref = candidate.input_payload_ref
        initial_summary_json = _initial_pass_summary(candidate)
        if candidate.pass_type == PASS_TYPE_ASSOCIATED_COHORT:
            assert candidate.prepared_cohort is not None
            derived_dataset_version_id, input_manifest_ref = _persist_cohort_dataset_version(
                db,
                session_id=session_id,
                analysis_set_id=candidate.analysis_set.analysis_set_id,
                pass_run_id=pass_run_id,
                prepared_cohort=candidate.prepared_cohort,
            )
            dataset_version_id = derived_dataset_version_id
            input_payload_ref = input_manifest_ref
            initial_summary_json = {
                **_json_clone(initial_summary_json),
                "derived_dataset_version_id": derived_dataset_version_id,
            }

        pass_run = L3PassRun(
            pass_run_id=pass_run_id,
            session_id=session_id,
            analysis_plan_id=analysis_plan.analysis_plan_id,
            analysis_set_id=candidate.analysis_set.analysis_set_id,
            pass_type=candidate.pass_type,
            engine_family=ENGINE_FAMILY_WRAPPED_QUANTITATIVE_ANALYSIS,
            status=PASS_STATUS_PLANNED,
            started_at=None,
            completed_at=None,
            input_payload_ref=input_payload_ref,
            output_payload_ref=None,
            summary_json=initial_summary_json,
            created_at=_utcnow(),
        )
        db.add(pass_run)
        db.flush()

        pass_run.status = PASS_STATUS_RUNNING
        pass_run.started_at = _utcnow()
        db.flush()

        assert dataset_version_id is not None
        try:
            analysis_run = run_analysis(
                db,
                dataset_version_id=dataset_version_id,
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
                "dataset_version_id": dataset_version_id,
                "selected_method_name": candidate.selected_method_name,
                "artifact_refs_json": [artifact.storage_ref for artifact in artifacts],
                "artifact_types_json": [artifact.artifact_type for artifact in artifacts],
                **(
                    {
                        "source_dataset_version_ids_json": list(
                            candidate.prepared_cohort.source_dataset_version_ids
                        ),
                        "column_map_json": [column.manifest_entry() for column in candidate.prepared_cohort.columns],
                    }
                    if candidate.prepared_cohort is not None
                    else {}
                ),
            },
        )
        has_warnings = _has_analysis_warnings(db, analysis_run_id=analysis_run.analysis_run_id)
        pass_run.status = PASS_STATUS_COMPLETED_WITH_WARNINGS if has_warnings else PASS_STATUS_COMPLETED
        pass_run.completed_at = _utcnow()
        pass_run.output_payload_ref = output_manifest_ref
        pass_run.summary_json = {
            **_json_clone(pass_run.summary_json),
            "analysis_run_id": analysis_run.analysis_run_id,
            "dataset_version_id": dataset_version_id,
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
            "source_gate": analysis_plan.plan_json.get("source_gate"),
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
            "source_gate": analysis_plan.plan_json.get("source_gate"),
        },
    }
    db.flush()

    return Layer3PassEntryResult(
        analysis_plan=analysis_plan,
        pass_runs=tuple(pass_runs),
    )
