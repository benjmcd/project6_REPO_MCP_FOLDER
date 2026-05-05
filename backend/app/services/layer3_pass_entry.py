from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any

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
from app.services.layer3_session_entry import (
    SESSION_STATUS_ACTIVE_EXECUTION,
    SESSION_STATUS_ACTIVE_PLANNING,
    SESSION_STATUS_COMPLETED,
    SESSION_STATUS_COMPLETED_WITH_WARNINGS,
    SESSION_STATUS_FAILED,
)
from app.services.layer3_typing_entry import (
    MODALITY_QUANTITATIVE,
    SET_TYPE_ASSOCIATED_COHORT,
    SET_TYPE_SINGLE_ITEM,
)
from app.services.layer3_qual_aps_execution import (
    ENGINE_FAMILY_QUAL_APS_DOCUMENT,
    PASS_SCOPE_SINGLE_APS_DOC_QUALITATIVE,
    QUAL_APS_METHOD_NAME,
    QUAL_APS_SOURCE_GATE,
    qualitative_aps_candidate_exclusion_reason,
)
from app.services.layer3_utils import (
    json_clone as _json_clone,
    stable_hash as _stable_hash,
    stable_json_bytes as _stable_json_bytes,
    utc_isoformat as _utc_isoformat,
    utcnow as _utcnow,
)

if TYPE_CHECKING:
    import pandas as pd


def recommend_analysis(*args: Any, **kwargs: Any) -> dict[str, Any]:
    from app.services.analysis import recommend_analysis as _recommend_analysis

    return _recommend_analysis(*args, **kwargs)


def run_analysis(*args: Any, **kwargs: Any) -> Any:
    from app.services.analysis import run_analysis as _run_analysis

    return _run_analysis(*args, **kwargs)


PLAN_STATUS_FORMED = "formed"
PLAN_STATUS_APPROVED = "approved"

PLAN_PREVIEW_HASH_SCHEMA_ID = "layer3.plan_preview_hash.v1"
PASS_TYPE_SINGLE_ITEM = "single_item"
ENGINE_FAMILY_WRAPPED_QUANTITATIVE_ANALYSIS = "wrapped_quantitative_analysis"

PASS_STATUS_PLANNED = "planned"
PASS_STATUS_SELECTED_NOT_STARTED = "selected_not_started"
PASS_STATUS_RUNNING = "running"
PASS_STATUS_COMPLETED = "completed"
PASS_STATUS_COMPLETED_WITH_WARNINGS = "completed_with_warnings"
PASS_STATUS_FAILED = "failed"

SOURCE_GATE_PASS_FREEZE = "06_GATEC_PASS_FREEZE"
SOURCE_GATE_COHORT_FREEZE = "07_GATEC_COHORT_FREEZE"
SOURCE_GATE_COHORT_DESC_FREEZE = "78_COHORT_FREEZE"
PLAN_VERSION = "gatec_pass_entry_v1"
PASS_SCOPE_QUANT_SINGLE_ITEM = "quantitative_single_item_dataset_version"
PASS_SCOPE_QUANT_ASSOCIATED_COHORT = "quantitative_associated_cohort_dataset_version"
PASS_TYPE_ASSOCIATED_COHORT = "associated_cohort"
COHORT_TIME_COLUMN = "observed_at"
COHORT_SHAPE_ALIGNED_WIDE_TABLE = "aligned_wide_table"
COHORT_REQUESTED_METHOD_KEY = "requested_method_name"
COHORT_REQUESTED_METHOD_SOURCE = "analysis_set.formation_basis_json.requested_method_name"
SUPPORTED_WRAPPED_QUANTITATIVE_METHODS = frozenset(
    {
        "cross_correlation",
        "descriptive_summary",
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
    source_variable_name: str
    stationarity_hint: str | None
    seasonality_flag: bool | None

    def manifest_entry(self) -> dict[str, Any]:
        return {
            "column_name": self.column_name,
            "analysis_unit_id": self.analysis_unit_id,
            "material_snapshot_id": self.material_snapshot_id,
            "dataset_version_id": self.dataset_version_id,
            "descriptor_id": self.descriptor_id,
            "source_variable_name": self.source_variable_name,
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
    engine_family: str = ENGINE_FAMILY_WRAPPED_QUANTITATIVE_ANALYSIS
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
    preview_hash: str
    admitted_sets: tuple[dict[str, Any], ...]
    excluded_sets: tuple[dict[str, Any], ...]
    planned_passes: tuple[dict[str, Any], ...]
    warnings: tuple[dict[str, Any], ...]
    owner_service_basis: dict[str, Any]
    owner_plan_payload: dict[str, Any]


@dataclass(frozen=True)
class Layer3PassEntryApprovalResult:
    analysis_plan: L3AnalysisPlan
    source_preview_id: str | None
    source_preview_hash: str
    approved_sets: tuple[dict[str, Any], ...]
    excluded_sets: tuple[dict[str, Any], ...]
    planned_passes: tuple[dict[str, Any], ...]
    warnings: tuple[dict[str, Any], ...]
    owner_service_basis: dict[str, Any]


@dataclass(frozen=True)
class Layer3SelectedPassExecutionResult:
    pass_run: L3PassRun
    status: str
    execution_started: bool
    analysis_run_id: str | None
    dataset_version_id: str | None
    selected_method_name: str | None
    output_payload_ref: str | None
    error_message: str | None = None


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


def _cohort_requested_method_name(analysis_set: L3AnalysisSet) -> str | None:
    requested = analysis_set.formation_basis_json.get(COHORT_REQUESTED_METHOD_KEY)
    if requested is None or not isinstance(requested, str):
        return None
    return requested or None


def _selected_cohort_planned_pass_error(
    *,
    pass_run: L3PassRun,
    planned_pass: dict[str, Any],
    summary: dict[str, Any],
) -> str | None:
    if pass_run.pass_type != PASS_TYPE_ASSOCIATED_COHORT:
        return "selected-pass associated-cohort source-breadth rejection: pass run is not associated_cohort"
    if str(planned_pass.get("analysis_set_id") or "") != pass_run.analysis_set_id:
        return "selected-pass associated-cohort provenance rejection: analysis_set_id binding is inconsistent"
    if planned_pass.get("pass_type") != PASS_TYPE_ASSOCIATED_COHORT:
        return "selected-pass associated-cohort source-breadth rejection: planned pass is not associated_cohort"
    if planned_pass.get("pass_scope") != PASS_SCOPE_QUANT_ASSOCIATED_COHORT:
        return "selected-pass associated-cohort source-breadth rejection: pass scope is not admitted"
    if planned_pass.get("selected_method_name") != "descriptive_summary":
        return "selected-pass associated-cohort method-name rejection: selected_method_name is not exactly descriptive_summary"
    if planned_pass.get(COHORT_REQUESTED_METHOD_KEY) != "descriptive_summary":
        return "selected-pass associated-cohort method-source rejection: requested_method_name is not exactly descriptive_summary"
    if planned_pass.get("requested_method_source") != COHORT_REQUESTED_METHOD_SOURCE:
        return "selected-pass associated-cohort method-source rejection: requested_method_source is not service-owned formation metadata"
    if planned_pass.get("cohort_shape") != COHORT_SHAPE_ALIGNED_WIDE_TABLE:
        return "selected-pass associated-cohort provenance rejection: cohort shape is not aligned_wide_table"
    if planned_pass.get("source_gate") != SOURCE_GATE_COHORT_DESC_FREEZE:
        return "selected-pass associated-cohort provenance rejection: source gate is not the descriptive cohort freeze"

    source_ids = planned_pass.get("source_dataset_version_ids_json")
    if not isinstance(source_ids, list) or not source_ids or any(not isinstance(item, str) or not item for item in source_ids):
        return "selected-pass associated-cohort provenance rejection: source dataset-version ids are missing"

    summary_planned_pass = summary.get("planned_pass")
    if not isinstance(summary_planned_pass, dict):
        return "selected-pass associated-cohort provenance rejection: selected pass summary is missing planned_pass"
    if summary_planned_pass != planned_pass:
        return "selected-pass associated-cohort provenance rejection: selected pass summary does not match planned_pass"
    if str(summary.get("analysis_plan_id") or "") != pass_run.analysis_plan_id:
        return "selected-pass associated-cohort provenance rejection: analysis_plan_id binding is inconsistent"
    if not str(summary.get("source_preview_id") or "").strip() or not str(summary.get("source_preview_hash") or "").strip():
        return "selected-pass associated-cohort provenance rejection: preview identity is missing"
    return None


def _prepare_selected_cohort_execution_input(
    db: Session,
    *,
    pass_run: L3PassRun,
    planned_pass: dict[str, Any],
    summary: dict[str, Any],
) -> tuple[str, str, dict[str, Any]]:
    contract_error = _selected_cohort_planned_pass_error(
        pass_run=pass_run,
        planned_pass=planned_pass,
        summary=summary,
    )
    if contract_error is not None:
        raise Layer3PassEntryError(contract_error)

    analysis_set = db.get(L3AnalysisSet, pass_run.analysis_set_id)
    if analysis_set is None or analysis_set.session_id != pass_run.session_id:
        raise Layer3PassEntryError(
            "selected-pass associated-cohort provenance rejection: analysis set is missing or session-mismatched"
        )
    if analysis_set.set_type != SET_TYPE_ASSOCIATED_COHORT:
        raise Layer3PassEntryError(
            "selected-pass associated-cohort source-breadth rejection: analysis set is not associated_cohort"
        )
    requested_method_name = _cohort_requested_method_name(analysis_set)
    if requested_method_name != "descriptive_summary":
        raise Layer3PassEntryError(
            "selected-pass associated-cohort method-source rejection: formation metadata is not exactly descriptive_summary"
        )

    _, unit_by_id, snapshot_by_id = _load_sets_units_and_snapshots(db, session_id=pass_run.session_id)
    analysis_unit_ids = list(analysis_set.analysis_unit_ids_json or [])
    prepared_cohort, exclusion_reason = _prepare_cohort_candidate(
        db,
        analysis_set=analysis_set,
        analysis_unit_ids=analysis_unit_ids,
        analysis_modality=analysis_set.formation_basis_json.get("analysis_modality"),
        unit_by_id=unit_by_id,
        snapshot_by_id=snapshot_by_id,
    )
    if prepared_cohort is None:
        raise Layer3PassEntryError(
            f"selected-pass associated-cohort provenance rejection: {exclusion_reason or 'cohort input is not admitted'}"
        )
    selected_method_name = _choose_cohort_method_name_or_raise(
        shaped_dataframe=prepared_cohort.shaped_dataframe,
        requested_method_name=requested_method_name,
    )
    if selected_method_name != "descriptive_summary":
        raise Layer3PassEntryError(
            "selected-pass associated-cohort method-name rejection: prepared cohort did not resolve to descriptive_summary"
        )

    planned_source_ids = [str(item) for item in planned_pass["source_dataset_version_ids_json"]]
    if list(prepared_cohort.source_dataset_version_ids) != planned_source_ids:
        raise Layer3PassEntryError(
            "selected-pass associated-cohort provenance rejection: source dataset-version ids do not match prepared input"
        )

    derived_dataset_version_id, input_manifest_ref = _persist_cohort_dataset_version(
        db,
        session_id=pass_run.session_id,
        analysis_set_id=analysis_set.analysis_set_id,
        pass_run_id=pass_run.pass_run_id,
        prepared_cohort=prepared_cohort,
        selected_method_name=selected_method_name,
        source_gate=SOURCE_GATE_COHORT_DESC_FREEZE,
    )
    cohort_metadata = {
        "pass_scope": PASS_SCOPE_QUANT_ASSOCIATED_COHORT,
        "source_gate": SOURCE_GATE_COHORT_DESC_FREEZE,
        "derived_dataset_version_id": derived_dataset_version_id,
        "source_dataset_version_ids_json": list(prepared_cohort.source_dataset_version_ids),
        "column_map_json": [column.manifest_entry() for column in prepared_cohort.columns],
        "cohort_shape": COHORT_SHAPE_ALIGNED_WIDE_TABLE,
        "requested_method_name": "descriptive_summary",
        "requested_method_source": COHORT_REQUESTED_METHOD_SOURCE,
    }
    return derived_dataset_version_id, input_manifest_ref, cohort_metadata


def _choose_cohort_method_name_or_raise(
    *,
    shaped_dataframe: pd.DataFrame,
    requested_method_name: str | None = None,
) -> str:
    numeric_columns = [column for column in shaped_dataframe.columns if column != COHORT_TIME_COLUMN]
    is_aligned_wide_table = COHORT_TIME_COLUMN in shaped_dataframe.columns and len(numeric_columns) >= 2
    if requested_method_name == "descriptive_summary":
        if is_aligned_wide_table:
            return "descriptive_summary"
        raise Layer3PassEntryError("shaped cohort descriptive_summary request does not satisfy aligned wide-table shape")
    if is_aligned_wide_table:
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
    import pandas as pd

    from app.services.dataframe_io import load_version_dataframe

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
                    source_variable_name=measure_variable.variable_name,
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
            requested_method_name = _cohort_requested_method_name(analysis_set)
            selected_method_name = _choose_cohort_method_name_or_raise(
                shaped_dataframe=prepared_cohort.shaped_dataframe,
                requested_method_name=requested_method_name,
            )
            source_gate = (
                SOURCE_GATE_COHORT_DESC_FREEZE
                if selected_method_name == "descriptive_summary"
                else SOURCE_GATE_COHORT_FREEZE
            )
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
                    source_gate=source_gate,
                    selected_method_name=selected_method_name,
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
        if analysis_unit.analysis_modality != MODALITY_QUANTITATIVE:
            if analysis_unit.analysis_modality == "qualitative":
                exclusion_reason = qualitative_aps_candidate_exclusion_reason(
                    db,
                    analysis_set=analysis_set,
                    analysis_unit=analysis_unit,
                    material_snapshot=snapshot,
                )
                if exclusion_reason is None:
                    admitted.append(
                        _AdmittedSetCandidate(
                            analysis_set=analysis_set,
                            analysis_units=(analysis_unit,),
                            snapshots=(snapshot,),
                            pass_type=PASS_TYPE_SINGLE_ITEM,
                            pass_scope=PASS_SCOPE_SINGLE_APS_DOC_QUALITATIVE,
                            source_gate=QUAL_APS_SOURCE_GATE,
                            selected_method_name=QUAL_APS_METHOD_NAME,
                            engine_family=ENGINE_FAMILY_QUAL_APS_DOCUMENT,
                            input_payload_ref=snapshot.payload_ref,
                        )
                    )
                    continue
                reason_code = exclusion_reason
            else:
                reason_code = "analysis_modality_not_admitted"
            excluded.append(
                _exclusion_entry(
                    analysis_set,
                    reason_code=reason_code,
                    analysis_modality=analysis_unit.analysis_modality,
                )
            )
            continue
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


def _is_single_aps_doc_qualitative_candidate(candidate: _AdmittedSetCandidate) -> bool:
    return (
        candidate.engine_family == ENGINE_FAMILY_QUAL_APS_DOCUMENT
        and candidate.pass_scope == PASS_SCOPE_SINGLE_APS_DOC_QUALITATIVE
        and candidate.selected_method_name == QUAL_APS_METHOD_NAME
        and candidate.source_gate == QUAL_APS_SOURCE_GATE
    )


def _planned_pass_source_fields(candidate: _AdmittedSetCandidate) -> dict[str, Any]:
    if candidate.dataset_version_id is not None:
        return {"dataset_version_id": candidate.dataset_version_id}
    if candidate.prepared_cohort is not None:
        return {"source_dataset_version_ids_json": list(candidate.prepared_cohort.source_dataset_version_ids)}
    if _is_single_aps_doc_qualitative_candidate(candidate):
        snapshot = candidate.snapshots[0]
        identity = snapshot.source_identity_json or {}
        return {
            "material_snapshot_id": snapshot.material_snapshot_id,
            "content_id": identity.get("content_id"),
            "content_contract_id": identity.get("content_contract_id"),
            "chunking_contract_id": identity.get("chunking_contract_id"),
        }
    raise Layer3PassEntryError(
        f"Layer 3 analysis set '{candidate.analysis_set.analysis_set_id}' has no admitted planned-pass source fields"
    )


def _plan_formation_reason(admitted: list[_AdmittedSetCandidate]) -> str:
    if any(_is_single_aps_doc_qualitative_candidate(candidate) for candidate in admitted):
        return "single_aps_doc_qualitative_pass_entry"
    return "quantitative_dataset_version_backed_gatec_only"


def _plan_source_gate(admitted: list[_AdmittedSetCandidate]) -> str:
    source_gates = {candidate.source_gate for candidate in admitted}
    if len(source_gates) == 1:
        return next(iter(source_gates))
    return "mixed_gatec_pass_entry"


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
                "engine_family": candidate.engine_family,
                "selected_method_name": candidate.selected_method_name,
                "source_gate": candidate.source_gate,
                **(
                    {
                        "cohort_shape": COHORT_SHAPE_ALIGNED_WIDE_TABLE,
                        **(
                            {
                                "requested_method_name": "descriptive_summary",
                                "requested_method_source": COHORT_REQUESTED_METHOD_SOURCE,
                            }
                            if candidate.selected_method_name == "descriptive_summary"
                            else {}
                        ),
                    }
                    if candidate.pass_type == PASS_TYPE_ASSOCIATED_COHORT
                    else {}
                ),
                **_planned_pass_source_fields(candidate),
            }
            for candidate in admitted
        ],
        "excluded_sets_json": _json_clone(excluded),
        "formation_reason": _plan_formation_reason(admitted),
        "source_gate": _plan_source_gate(admitted),
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
        "engine_family": candidate.engine_family,
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
        "method_family": (
            "repo_supported_qualitative_aps_document"
            if _is_single_aps_doc_qualitative_candidate(candidate)
            else "repo_supported_quantitative"
        ),
        "engine_family": candidate.engine_family,
        "selected_method_name": candidate.selected_method_name,
        "execution_status": "not_started",
        "preview_only": True,
    }
    if candidate.dataset_version_id is not None:
        result["dataset_version_id"] = candidate.dataset_version_id
    if candidate.prepared_cohort is not None:
        result["source_dataset_version_ids"] = list(candidate.prepared_cohort.source_dataset_version_ids)
    if _is_single_aps_doc_qualitative_candidate(candidate):
        result.update(_planned_pass_source_fields(candidate))
    return result


def _approval_admitted_entry(item: dict[str, Any]) -> dict[str, Any]:
    result = dict(item)
    result["readiness"] = "approved"
    return result


def _preview_result_from_basis(
    *,
    session_id: str,
    admitted: list[_AdmittedSetCandidate],
    excluded: list[dict[str, Any]],
    analysis_sets: list[L3AnalysisSet],
    unit_by_id: dict[str, L3AnalysisUnit],
    snapshot_by_id: dict[str, L3MaterialSnapshot],
) -> Layer3PassEntryPreviewResult:
    plan_payload = _plan_payload(admitted, excluded)
    analysis_set_by_id = {analysis_set.analysis_set_id: analysis_set for analysis_set in analysis_sets}
    admitted_sets = tuple(_preview_admitted_entry(candidate) for candidate in admitted)
    excluded_sets = tuple(
        _preview_excluded_entry(
            item,
            analysis_set_by_id=analysis_set_by_id,
            unit_by_id=unit_by_id,
            snapshot_by_id=snapshot_by_id,
        )
        for item in excluded
    )
    planned_passes = tuple(_preview_planned_pass(candidate) for candidate in admitted)
    warnings = []
    if excluded:
        warnings.append(
            {
                "reason_code": "partial_plan_preview",
                "message": "Some analysis sets are excluded by the current Gate C pass-entry rules.",
                "excluded_set_count": len(excluded),
            }
        )
    owner_service_basis = {
        "service": "backend/app/services/layer3_pass_entry.py",
        "mode": "read_only_preview",
        "source_gate": plan_payload["source_gate"],
        "owner_plan_version": PLAN_VERSION,
        "preview_hash_schema_id": PLAN_PREVIEW_HASH_SCHEMA_ID,
    }
    preview_basis = {
        "schema_id": PLAN_PREVIEW_HASH_SCHEMA_ID,
        "session_id": session_id,
        "admitted_sets": admitted_sets,
        "excluded_sets": excluded_sets,
        "planned_passes": planned_passes,
        "warnings": tuple(warnings),
        "owner_service_basis": owner_service_basis,
        "owner_plan_payload": plan_payload,
    }
    return Layer3PassEntryPreviewResult(
        session_id=session_id,
        preview_hash=_stable_hash(preview_basis),
        admitted_sets=admitted_sets,
        excluded_sets=excluded_sets,
        planned_passes=planned_passes,
        warnings=tuple(warnings),
        owner_service_basis=owner_service_basis,
        owner_plan_payload=_json_clone(plan_payload),
    )


def _load_admitted_preview_basis(
    db: Session,
    *,
    session_id: str,
) -> tuple[
    L3Session,
    list[_AdmittedSetCandidate],
    list[dict[str, Any]],
    Layer3PassEntryPreviewResult,
]:
    session = _load_session_or_raise(db, session_id=session_id)
    _ensure_session_not_yet_passed(db, session_id=session_id)
    analysis_sets, unit_by_id, snapshot_by_id = _load_sets_units_and_snapshots(db, session_id=session_id)
    admitted, excluded = _classify_sets(
        db,
        analysis_sets=analysis_sets,
        unit_by_id=unit_by_id,
        snapshot_by_id=snapshot_by_id,
    )
    qualitative_admitted = [
        candidate for candidate in admitted if _is_single_aps_doc_qualitative_candidate(candidate)
    ]
    if qualitative_admitted and (len(qualitative_admitted) != 1 or len(admitted) != 1 or len(analysis_sets) != 1):
        raise Layer3PassEntryError(
            "single_aps_doc_qualitative_pass admits exactly one qualitative APS document analysis set"
        )
    if not admitted:
        raise Layer3PassEntryError(
            f"Layer 3 session '{session_id}' has no admissible analysis sets for Gate C pass entry"
        )
    preview = _preview_result_from_basis(
        session_id=session_id,
        admitted=admitted,
        excluded=excluded,
        analysis_sets=analysis_sets,
        unit_by_id=unit_by_id,
        snapshot_by_id=snapshot_by_id,
    )
    return session, admitted, excluded, preview


def preview_pass_entry(db: Session, *, session_id: str) -> Layer3PassEntryPreviewResult:
    """Return the Gate C pass-entry plan basis without materializing or executing it."""

    _, _, _, preview = _load_admitted_preview_basis(db, session_id=session_id)
    return preview


def approve_pass_entry_plan(
    db: Session,
    *,
    session_id: str,
    preview_hash: str | None = None,
    source_preview_id: str | None = None,
    approved_by_operator: bool = True,
) -> Layer3PassEntryApprovalResult:
    """Persist operator approval of the current pass-entry plan without executing it."""

    if not approved_by_operator:
        raise Layer3PassEntryError("operator confirmation is required for Layer 3 plan approval")

    session, admitted, excluded, preview = _load_admitted_preview_basis(db, session_id=session_id)
    if preview_hash is not None and preview_hash != preview.preview_hash:
        raise Layer3PassEntryError("Layer 3 plan approval preview hash mismatch")

    approved_at = _utcnow()
    owner_service_basis = {
        **_json_clone(preview.owner_service_basis),
        "mode": "operator_approved_plan_only",
        "source_gate": "plan_approval",
    }
    approved_plan_json = {
        **_json_clone(preview.owner_plan_payload),
        "approval_only": True,
        "execution_started": False,
        "source_preview_id": source_preview_id,
        "source_preview_hash": preview.preview_hash,
        "approved_by_operator": True,
        "approved_at": _utc_isoformat(approved_at),
        "approved_sets_json": [_approval_admitted_entry(item) for item in preview.admitted_sets],
        "warnings_json": [dict(item) for item in preview.warnings],
        "owner_service_basis": owner_service_basis,
    }
    analysis_plan = L3AnalysisPlan(
        analysis_plan_id=uuid_str(),
        session_id=session_id,
        analysis_set_ids_json=[candidate.analysis_set.analysis_set_id for candidate in admitted],
        status=PLAN_STATUS_APPROVED,
        approved_by_operator=True,
        approved_at=approved_at,
        plan_json=approved_plan_json,
        created_at=approved_at,
    )
    db.add(analysis_plan)
    session.summary_json = {
        **_json_clone(session.summary_json),
        "plan_approval": {
            "analysis_plan_id": analysis_plan.analysis_plan_id,
            "approved_set_count": len(admitted),
            "excluded_set_count": len(excluded),
            "planned_pass_count": len(preview.planned_passes),
            "source_preview_id": source_preview_id,
            "source_preview_hash": preview.preview_hash,
            "source_gate": preview.owner_plan_payload.get("source_gate"),
            "approval_only": True,
            "execution_started": False,
        },
    }
    db.flush()
    return Layer3PassEntryApprovalResult(
        analysis_plan=analysis_plan,
        source_preview_id=source_preview_id,
        source_preview_hash=preview.preview_hash,
        approved_sets=tuple(_approval_admitted_entry(item) for item in preview.admitted_sets),
        excluded_sets=tuple(dict(item) for item in preview.excluded_sets),
        planned_passes=tuple(dict(item) for item in preview.planned_passes),
        warnings=tuple(dict(item) for item in preview.warnings),
        owner_service_basis=owner_service_basis,
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
        "engine_family": candidate.engine_family,
        "source_gate": candidate.source_gate,
        "analysis_run_id": None,
    }
    if candidate.pass_type == PASS_TYPE_SINGLE_ITEM:
        snapshot = candidate.snapshots[0]
        summary["source_snapshot_id"] = snapshot.material_snapshot_id
        summary["source_snapshot_payload_ref"] = snapshot.payload_ref
        if _is_single_aps_doc_qualitative_candidate(candidate):
            summary["source_shape"] = snapshot.source_shape
            summary.update(_planned_pass_source_fields(candidate))
    else:
        assert candidate.prepared_cohort is not None
        summary["derived_dataset_version_id"] = None
        summary["source_dataset_version_ids_json"] = list(candidate.prepared_cohort.source_dataset_version_ids)
        summary["column_map_json"] = [column.manifest_entry() for column in candidate.prepared_cohort.columns]
        summary["cohort_shape"] = COHORT_SHAPE_ALIGNED_WIDE_TABLE
        if candidate.selected_method_name == "descriptive_summary":
            summary["requested_method_name"] = "descriptive_summary"
            summary["requested_method_source"] = COHORT_REQUESTED_METHOD_SOURCE
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
    selected_method_name: str,
    source_gate: str,
) -> tuple[str, str]:
    from app.services.dataframe_io import persist_dataframe_as_version_rows

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
                    "source_variable_name": prepared_column.source_variable_name,
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
            "source_gate": source_gate,
            "selected_method_name": selected_method_name,
            "cohort_shape": COHORT_SHAPE_ALIGNED_WIDE_TABLE,
            **(
                {
                    "requested_method_name": "descriptive_summary",
                    "requested_method_source": COHORT_REQUESTED_METHOD_SOURCE,
                }
                if selected_method_name == "descriptive_summary"
                else {}
            ),
        },
    )
    return version.dataset_version_id, manifest_ref


def _persist_output_manifest(*, pass_run_id: str, payload: dict[str, Any]) -> str:
    output_path = _layer3_artifact_dir() / f"l3_pass_run_{pass_run_id}.json"
    output_path.write_text(json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False), encoding="utf-8")
    return str(output_path)


def _has_analysis_warnings(db: Session, *, analysis_run_id: str) -> bool:
    return db.query(CaveatNote).filter(CaveatNote.analysis_run_id == analysis_run_id).count() > 0


def execute_selected_pass_run(
    db: Session,
    *,
    pass_run: L3PassRun,
    planned_pass: dict[str, Any],
    client_request_id: str,
) -> Layer3SelectedPassExecutionResult:
    """Execute one preselected workbench pass without creating plan or pass-run rows."""

    pass_run_id = pass_run.pass_run_id
    if pass_run.status != PASS_STATUS_SELECTED_NOT_STARTED:
        raise Layer3PassEntryError(
            f"Selected pass run '{pass_run_id}' must be selected_not_started before execution start"
        )
    if pass_run.output_payload_ref:
        raise Layer3PassEntryError(f"Selected pass run '{pass_run_id}' already has output metadata")
    if pass_run.engine_family != ENGINE_FAMILY_WRAPPED_QUANTITATIVE_ANALYSIS:
        raise Layer3PassEntryError(
            f"Selected pass run '{pass_run_id}' uses unsupported engine family '{pass_run.engine_family}'"
        )

    summary = _json_clone(pass_run.summary_json or {})
    if summary.get("analysis_run_id"):
        raise Layer3PassEntryError(f"Selected pass run '{pass_run_id}' already has an analysis_run_id")

    planned_engine_family = str(planned_pass.get("engine_family") or pass_run.engine_family)
    if planned_engine_family != ENGINE_FAMILY_WRAPPED_QUANTITATIVE_ANALYSIS:
        raise Layer3PassEntryError(
            f"Selected pass run '{pass_run_id}' planned unsupported engine family '{planned_engine_family}'"
        )
    planned_pass_type = str(planned_pass.get("pass_type") or pass_run.pass_type)
    cohort_execution_metadata: dict[str, Any] | None = None
    original_input_payload_ref = pass_run.input_payload_ref
    input_payload_ref = pass_run.input_payload_ref
    if planned_pass_type == PASS_TYPE_SINGLE_ITEM:
        dataset_version_id = str(planned_pass.get("dataset_version_id") or summary.get("dataset_version_id") or "").strip()
        selected_method_name = str(
            planned_pass.get("selected_method_name") or summary.get("selected_method_name") or ""
        ).strip()
        if not dataset_version_id:
            raise Layer3PassEntryError(f"Selected pass run '{pass_run_id}' has no dataset_version_id")
        if selected_method_name not in SUPPORTED_WRAPPED_QUANTITATIVE_METHODS:
            raise Layer3PassEntryError(
                f"Selected pass run '{pass_run_id}' uses unsupported method '{selected_method_name}'"
            )
    elif planned_pass_type == PASS_TYPE_ASSOCIATED_COHORT:
        dataset_version_id, input_payload_ref, cohort_execution_metadata = _prepare_selected_cohort_execution_input(
            db,
            pass_run=pass_run,
            planned_pass=planned_pass,
            summary=summary,
        )
        selected_method_name = "descriptive_summary"
    else:
        raise Layer3PassEntryError(
            f"Selected pass run '{pass_run_id}' uses source breadth outside this execution-start slice"
        )

    started_at = _utcnow()
    pass_run.status = PASS_STATUS_RUNNING
    pass_run.started_at = started_at
    pass_run.input_payload_ref = input_payload_ref
    pass_run.summary_json = {
        **summary,
        **(cohort_execution_metadata or {}),
        "execution_started": True,
        "analysis_run_id": None,
        "dataset_version_id": dataset_version_id,
        "selected_method_name": selected_method_name,
        "input_payload_ref": input_payload_ref,
        "analysis_execution_start": {
            "schema_id": "layer3.analysis_execution_start_state.v1",
            "client_request_id": client_request_id,
            "state": "execution_pass_running",
            "started_at": _utc_isoformat(started_at),
        },
    }
    db.flush()

    try:
        analysis_run = run_analysis(
            db,
            dataset_version_id=dataset_version_id,
            method_name=selected_method_name,
            goal_type=None,
            parameters={},
            annotation_window_id=None,
        )
    except Exception as exc:
        db.rollback()
        failed_pass_run = db.get(L3PassRun, pass_run_id)
        if failed_pass_run is None:
            raise Layer3PassEntryError(f"Selected pass run '{pass_run_id}' disappeared during execution") from exc
        completed_at = _utcnow()
        failed_summary = _json_clone(failed_pass_run.summary_json or {})
        if cohort_execution_metadata is not None:
            failed_summary.pop("dataset_version_id", None)
            failed_summary.pop("derived_dataset_version_id", None)
            failed_summary.pop("input_payload_ref", None)
        failed_cohort_metadata = _json_clone(cohort_execution_metadata or {})
        cohort_dataset_resolvable = (
            cohort_execution_metadata is not None
            and bool(dataset_version_id)
            and db.get(DatasetVersion, dataset_version_id) is not None
        )
        if failed_cohort_metadata and not cohort_dataset_resolvable:
            failed_cohort_metadata.pop("derived_dataset_version_id", None)
        failed_pass_run.status = PASS_STATUS_FAILED
        failed_pass_run.started_at = started_at
        failed_pass_run.completed_at = completed_at
        if cohort_execution_metadata is None or cohort_dataset_resolvable:
            failed_pass_run.input_payload_ref = input_payload_ref
        else:
            failed_pass_run.input_payload_ref = original_input_payload_ref
        failed_pass_run.summary_json = {
            **failed_summary,
            **failed_cohort_metadata,
            "execution_started": True,
            "analysis_run_id": None,
            "selected_method_name": selected_method_name,
            "error": str(exc),
            "analysis_execution_start": {
                "schema_id": "layer3.analysis_execution_start_state.v1",
                "client_request_id": client_request_id,
                "state": "execution_pass_failed",
                "started_at": _utc_isoformat(started_at),
                "completed_at": _utc_isoformat(completed_at),
                "error": str(exc),
            },
        }
        if cohort_execution_metadata is None or cohort_dataset_resolvable:
            failed_pass_run.summary_json = {
                **failed_pass_run.summary_json,
                "dataset_version_id": dataset_version_id,
                "input_payload_ref": input_payload_ref,
            }
        db.flush()
        return Layer3SelectedPassExecutionResult(
            pass_run=failed_pass_run,
            status=PASS_STATUS_FAILED,
            execution_started=True,
            analysis_run_id=None,
            dataset_version_id=(
                dataset_version_id
                if cohort_execution_metadata is None or cohort_dataset_resolvable
                else None
            ),
            selected_method_name=selected_method_name,
            output_payload_ref=None,
            error_message=str(exc),
        )

    db.refresh(pass_run)
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
            "analysis_set_id": pass_run.analysis_set_id,
            "dataset_version_id": dataset_version_id,
            "selected_method_name": selected_method_name,
            "artifact_refs_json": [artifact.storage_ref for artifact in artifacts],
            "artifact_types_json": [artifact.artifact_type for artifact in artifacts],
            "source_gate": planned_pass.get("source_gate"),
            **(cohort_execution_metadata or {}),
        },
    )
    has_warnings = _has_analysis_warnings(db, analysis_run_id=analysis_run.analysis_run_id)
    completed_at = _utcnow()
    pass_run.status = PASS_STATUS_COMPLETED_WITH_WARNINGS if has_warnings else PASS_STATUS_COMPLETED
    pass_run.completed_at = completed_at
    pass_run.output_payload_ref = output_manifest_ref
    pass_run.summary_json = {
        **_json_clone(pass_run.summary_json or {}),
        **(cohort_execution_metadata or {}),
        "execution_started": True,
        "analysis_run_id": analysis_run.analysis_run_id,
        "dataset_version_id": dataset_version_id,
        "selected_method_name": selected_method_name,
        "input_payload_ref": input_payload_ref,
        "artifact_refs_json": [artifact.storage_ref for artifact in artifacts],
        "artifact_types_json": [artifact.artifact_type for artifact in artifacts],
        "pass_status_from_analysis": analysis_run.status,
        "analysis_execution_start": {
            "schema_id": "layer3.analysis_execution_start_state.v1",
            "client_request_id": client_request_id,
            "state": "execution_pass_completed",
            "started_at": _utc_isoformat(pass_run.started_at),
            "completed_at": _utc_isoformat(completed_at),
        },
    }
    db.flush()

    return Layer3SelectedPassExecutionResult(
        pass_run=pass_run,
        status=pass_run.status,
        execution_started=True,
        analysis_run_id=analysis_run.analysis_run_id,
        dataset_version_id=dataset_version_id,
        selected_method_name=selected_method_name,
        output_payload_ref=output_manifest_ref,
    )


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
        if candidate.engine_family != ENGINE_FAMILY_WRAPPED_QUANTITATIVE_ANALYSIS:
            raise Layer3PassEntryError(
                "Gate C materialize_pass_entry still admits only wrapped quantitative immediate execution; "
                "use plan approval, execution selection, and selected-pass start for single APS-document qualitative execution"
            )
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
                selected_method_name=candidate.selected_method_name,
                source_gate=candidate.source_gate,
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
                "source_gate": candidate.source_gate,
                **(
                    {
                        "source_dataset_version_ids_json": list(
                            candidate.prepared_cohort.source_dataset_version_ids
                        ),
                        "column_map_json": [column.manifest_entry() for column in candidate.prepared_cohort.columns],
                        "cohort_shape": COHORT_SHAPE_ALIGNED_WIDE_TABLE,
                        **(
                            {
                                "requested_method_name": "descriptive_summary",
                                "requested_method_source": COHORT_REQUESTED_METHOD_SOURCE,
                            }
                            if candidate.selected_method_name == "descriptive_summary"
                            else {}
                        ),
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
            "artifact_types_json": [artifact.artifact_type for artifact in artifacts],
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
