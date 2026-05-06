from __future__ import annotations

from typing import Any, Iterable

from app.models.models import L3OutputPackage, L3ReconciliationRecord
from app.services.layer3_package_entry import (
    PACKAGE_KIND_CANONICAL_INTERNAL,
    PACKAGE_KIND_REVIEW_FACING,
    PACKAGE_KIND_USER_FACING,
)
from app.services.layer3_pass_entry import (
    COHORT_REQUESTED_METHOD_SOURCE,
    COHORT_SHAPE_ALIGNED_WIDE_TABLE,
    PASS_SCOPE_QUANT_ASSOCIATED_COHORT,
    PASS_TYPE_ASSOCIATED_COHORT,
    SOURCE_GATE_COHORT_DESC_FREEZE,
)
from app.services.layer3_utils import json_clone, stable_id


PACKAGE_REVIEW_PREVIEW_STATE_SCHEMA_ID = "layer3.package_review_preview_state.v1"
PACKAGE_REVIEW_PREVIEW_READY_STATE = "package_review_preview_ready"
PACKAGE_REVIEW_PREVIEW_DOWNSTREAM_UNAVAILABLE = (
    "package_review_submit",
    "handoff",
    "export",
)
COHORT_PACKAGE_REVIEW_PREVIEW_DOWNSTREAM_UNAVAILABLE = (
    "package_review_submit",
    "handoff",
    "export",
    "aps_handoff",
    "external_export_download",
    "connector",
)
PACKAGE_REVIEW_PREVIEW_CANDIDATE_KINDS = (
    PACKAGE_KIND_CANONICAL_INTERNAL,
    PACKAGE_KIND_USER_FACING,
    PACKAGE_KIND_REVIEW_FACING,
)
PACKAGE_REVIEW_SUBMIT_STATE_SCHEMA_ID = "layer3.package_review_submit_state.v1"
HANDOFF_EXPORT_PREPARE_STATE_SCHEMA_ID = "layer3.handoff_export_prepare_state.v1"
APS_HANDOFF_DISPATCH_STATE_SCHEMA_ID = "layer3.aps_handoff_dispatch_state.v1"
EXTERNAL_EXPORT_DOWNLOAD_PREPARE_STATE_SCHEMA_ID = "layer3.external_export_download_prepare_state.v1"


def reconciliation_state(
    reconciliation: L3ReconciliationRecord | None,
    *,
    state_key: str,
    schema_id: str,
) -> dict[str, Any] | None:
    if reconciliation is None:
        return None
    state = (reconciliation.summary_json or {}).get(state_key)
    if not isinstance(state, dict):
        return None
    if state.get("schema_id") != schema_id:
        return None
    return state


def package_review_submit_from_reconciliation(
    reconciliation: L3ReconciliationRecord | None,
) -> dict[str, Any] | None:
    return reconciliation_state(
        reconciliation,
        state_key="package_review_submit",
        schema_id=PACKAGE_REVIEW_SUBMIT_STATE_SCHEMA_ID,
    )


def handoff_export_prepare_from_reconciliation(
    reconciliation: L3ReconciliationRecord | None,
) -> dict[str, Any] | None:
    return reconciliation_state(
        reconciliation,
        state_key="handoff_export_prepare",
        schema_id=HANDOFF_EXPORT_PREPARE_STATE_SCHEMA_ID,
    )


def aps_handoff_dispatch_from_reconciliation(
    reconciliation: L3ReconciliationRecord | None,
) -> dict[str, Any] | None:
    return reconciliation_state(
        reconciliation,
        state_key="aps_handoff_dispatch",
        schema_id=APS_HANDOFF_DISPATCH_STATE_SCHEMA_ID,
    )


def external_export_download_prepare_from_reconciliation(
    reconciliation: L3ReconciliationRecord | None,
) -> dict[str, Any] | None:
    return reconciliation_state(
        reconciliation,
        state_key="external_export_download_prepare",
        schema_id=EXTERNAL_EXPORT_DOWNLOAD_PREPARE_STATE_SCHEMA_ID,
    )


def review_state_is_admitted_associated_cohort(review_state: dict[str, Any] | None) -> bool:
    if not isinstance(review_state, dict):
        return False
    source_dataset_version_ids = review_state.get("source_dataset_version_ids")
    return bool(
        review_state.get("pass_type") == PASS_TYPE_ASSOCIATED_COHORT
        and review_state.get("pass_scope") == PASS_SCOPE_QUANT_ASSOCIATED_COHORT
        and review_state.get("selected_method_name") == "descriptive_summary"
        and review_state.get("source_gate") == SOURCE_GATE_COHORT_DESC_FREEZE
        and isinstance(source_dataset_version_ids, list)
        and len(source_dataset_version_ids) > 0
        and review_state.get("cohort_shape") == COHORT_SHAPE_ALIGNED_WIDE_TABLE
        and review_state.get("requested_method_name") == "descriptive_summary"
        and review_state.get("requested_method_source") == COHORT_REQUESTED_METHOD_SOURCE
    )


def package_source_shape(
    *,
    output_metadata_summary: dict[str, Any],
    pass_summary: dict[str, Any],
) -> str | None:
    cohort_shape = str(output_metadata_summary.get("cohort_shape") or pass_summary.get("cohort_shape") or "").strip()
    if cohort_shape:
        return cohort_shape
    dataset_version_id = str(
        output_metadata_summary.get("dataset_version_id") or pass_summary.get("dataset_version_id") or ""
    ).strip()
    if dataset_version_id:
        return "dataset_version"
    return None


def package_source_dataset_version_ids(
    *,
    output_metadata_summary: dict[str, Any],
    pass_summary: dict[str, Any],
) -> list[str]:
    source_dataset_version_ids = output_metadata_summary.get("source_dataset_version_ids")
    if not isinstance(source_dataset_version_ids, list):
        source_dataset_version_ids = pass_summary.get("source_dataset_version_ids_json")
    if isinstance(source_dataset_version_ids, list) and source_dataset_version_ids:
        return [str(item) for item in source_dataset_version_ids if str(item or "").strip()]
    dataset_version_id = str(
        output_metadata_summary.get("dataset_version_id") or pass_summary.get("dataset_version_id") or ""
    ).strip()
    return [dataset_version_id] if dataset_version_id else []


def package_review_preview_hash(
    *,
    session_id: str,
    analysis_plan_id: str,
    pass_run_id: str,
    preview_id: str,
    preview_hash: str,
    analysis_run_id: str | None,
    result_review_record_ref: str | None,
    output_metadata_summary: dict[str, Any],
) -> str:
    return stable_id(
        "l3-package-preview",
        {
            "schema_id": "layer3.package_review_preview_hash.v1",
            "session_id": session_id,
            "analysis_plan_id": analysis_plan_id,
            "pass_run_id": pass_run_id,
            "preview_id": preview_id,
            "preview_hash": preview_hash,
            "analysis_run_id": analysis_run_id,
            "result_review_record_ref": result_review_record_ref,
            "output_payload_ref": output_metadata_summary.get("output_payload_ref"),
            "artifact_refs": output_metadata_summary.get("artifact_refs") or [],
            "artifact_types": output_metadata_summary.get("artifact_types") or [],
            "candidate_package_kinds": list(PACKAGE_REVIEW_PREVIEW_CANDIDATE_KINDS),
        },
    )


def package_owner_compatibility(
    *,
    session: Any,
    pass_run: Any,
    output_metadata_summary: dict[str, Any],
    review_state: dict[str, Any],
    approved_review_state: str,
    associated_cohort_preview: bool = False,
) -> dict[str, Any]:
    session_summary = session.summary_json or {}
    pass_summary = pass_run.summary_json or {}
    required_inputs = {
        "selected_pass_output_metadata": output_metadata_summary.get("readable") is True,
        "approved_result_review": review_state.get("review_state") == approved_review_state,
    }
    if not associated_cohort_preview:
        required_inputs = {
            "phase1a_loading_closure": isinstance(session_summary.get("phase1a_loading_closure"), dict),
            "pass_entry": isinstance(session_summary.get("pass_entry"), dict),
            **required_inputs,
        }
    missing_inputs = sorted(key for key, present in required_inputs.items() if not present)
    construction_compatible = bool(not missing_inputs)
    return {
        "schema_id": "layer3.package_owner_compatibility.v1",
        "owner_service": "layer3_package_entry.materialize_package_entry",
        "assessment_basis": [
            "existing_gate_d_package_owner_service_contract",
            "current_workbench_selected_pass_result_review_state",
            "read_only_selected_pass_output_metadata",
        ],
        "materialize_package_entry_callable": False,
        "workbench_package_commit_callable": construction_compatible,
        "preview_candidate_projection_compatible": True,
        "construction_compatible_with_current_workbench_state": construction_compatible,
        "missing_owner_service_inputs": missing_inputs,
        "selected_pass_status": pass_run.status,
        "pass_type": pass_run.pass_type,
        "pass_scope": output_metadata_summary.get("pass_scope") or pass_summary.get("pass_scope"),
        "source_gate": output_metadata_summary.get("source_gate") or pass_summary.get("source_gate"),
        "source_preview_id": pass_summary.get("source_preview_id"),
        "source_preview_hash": pass_summary.get("source_preview_hash"),
        "status": (
            "associated_cohort_construction_preconditions_satisfied"
            if associated_cohort_preview and construction_compatible
            else "construction_preconditions_satisfied_but_call_deferred"
            if construction_compatible
            else "construction_preconditions_missing"
        ),
        "reason": (
            "Associated-cohort package construction is admitted for this exact approved descriptive cohort review."
            if associated_cohort_preview and construction_compatible
            else "Current state can be assessed against the owner service, but this endpoint remains read-only."
            if construction_compatible
            else "Current workbench state lacks full Gate D package-entry inputs; candidate projection remains preview-only."
        ),
    }


def package_review_candidate_projection(*, package_commit_enabled: bool = True) -> list[dict[str, Any]]:
    readiness_reason = (
        "candidate family is eligible for bounded package construction commit"
        if package_commit_enabled
        else "candidate family is preview-only for associated-cohort review; package construction is deferred"
    )
    return [
        {
            "package_kind": package_kind,
            "preview_only": True,
            "package_commit_enabled": package_commit_enabled,
            "package_review_submit_enabled": False,
            "handoff_enabled": False,
            "readiness_reason": readiness_reason,
        }
        for package_kind in PACKAGE_REVIEW_PREVIEW_CANDIDATE_KINDS
    ]


def package_review_preview_summary(
    review_state: dict[str, Any] | None,
    *,
    approved_review_state: str,
) -> dict[str, Any]:
    approved = bool(
        isinstance(review_state, dict)
        and review_state.get("review_state") == approved_review_state
        and review_state.get("operator_decision") == "approved"
        and int(review_state.get("unresolved_trace_count") or 0) == 0
    )
    associated_cohort = bool(review_state_is_admitted_associated_cohort(review_state))
    downstream_unavailable = (
        COHORT_PACKAGE_REVIEW_PREVIEW_DOWNSTREAM_UNAVAILABLE
        if associated_cohort
        else PACKAGE_REVIEW_PREVIEW_DOWNSTREAM_UNAVAILABLE
    )
    package_commit_enabled = bool(approved)
    return {
        "schema_id": PACKAGE_REVIEW_PREVIEW_STATE_SCHEMA_ID,
        "available": approved,
        "state": PACKAGE_REVIEW_PREVIEW_READY_STATE if approved else None,
        "result_review_state": review_state.get("review_state") if isinstance(review_state, dict) else None,
        "result_review_record_ref": review_state.get("review_record_ref") if isinstance(review_state, dict) else None,
        "requires_preview_endpoint_validation": True,
        "package_review_preview_enabled": approved,
        "package_commit_enabled": package_commit_enabled,
        "package_review_enabled": False,
        "handoff_enabled": False,
        "candidate_package_kinds": (
            package_review_candidate_projection(package_commit_enabled=package_commit_enabled)
            if approved
            else []
        ),
        "pass_type": review_state.get("pass_type") if isinstance(review_state, dict) else None,
        "pass_scope": review_state.get("pass_scope") if isinstance(review_state, dict) else None,
        "selected_method_name": review_state.get("selected_method_name") if isinstance(review_state, dict) else None,
        "source_gate": review_state.get("source_gate") if isinstance(review_state, dict) else None,
        "source_dataset_version_ids": (
            json_clone(review_state.get("source_dataset_version_ids") or [])
            if isinstance(review_state, dict)
            else []
        ),
        "cohort_shape": review_state.get("cohort_shape") if isinstance(review_state, dict) else None,
        "downstream_unavailable": list(downstream_unavailable),
    }


def state_downstream_unavailable(
    state: Any,
    *,
    fallback: tuple[str, ...],
) -> tuple[str, ...]:
    values = state.get("downstream_unavailable") if isinstance(state, dict) else None
    if isinstance(values, (list, tuple)) and values:
        return tuple(str(item) for item in values)
    return fallback


def active_downstream_unavailable(
    *,
    transitions: Iterable[tuple[Any, str, Any, tuple[str, ...]]],
    default_state: Any,
    default_fallback: tuple[str, ...],
) -> tuple[str, ...]:
    for completed_state, completed_value, next_state, next_fallback in transitions:
        if isinstance(completed_state, dict) and completed_state.get("state") == completed_value:
            return state_downstream_unavailable(next_state, fallback=next_fallback)
    return state_downstream_unavailable(default_state, fallback=default_fallback)


def packages_in_kind_order(
    packages: list[L3OutputPackage],
    *,
    package_kinds: Iterable[str],
) -> list[L3OutputPackage]:
    packages_by_kind = {package.package_kind: package for package in packages}
    return [packages_by_kind[package_kind] for package_kind in package_kinds]


def packages_with_kinds(
    packages: list[L3OutputPackage],
    *,
    package_kinds: Iterable[str],
) -> list[L3OutputPackage]:
    source_kinds = set(package_kinds)
    return [package for package in packages if package.package_kind in source_kinds]


def packages_in_review_order(packages: list[L3OutputPackage]) -> list[L3OutputPackage]:
    return packages_in_kind_order(packages, package_kinds=PACKAGE_REVIEW_PREVIEW_CANDIDATE_KINDS)


def review_source_packages(packages: list[L3OutputPackage]) -> list[L3OutputPackage]:
    return packages_with_kinds(packages, package_kinds=PACKAGE_REVIEW_PREVIEW_CANDIDATE_KINDS)


def dispatched_package_id(
    dispatch_state: dict[str, Any] | None,
    *,
    dispatched_state: str,
    expected_package_kind: str,
) -> str | None:
    if not isinstance(dispatch_state, dict):
        return None
    if dispatch_state.get("aps_handoff_state") != dispatched_state:
        return None
    if dispatch_state.get("aps_output_package_kind") != expected_package_kind:
        return None
    output_package_id = str(dispatch_state.get("aps_output_package_id") or "").strip()
    return output_package_id or None


def unexpected_package_kinds(
    packages: list[L3OutputPackage],
    *,
    source_kinds: Iterable[str],
    aps_handoff_dispatch_state: dict[str, Any] | None,
    aps_dispatched_state: str,
    aps_package_kind: str,
) -> list[str]:
    allowed_source_kinds = set(source_kinds)
    allowed_aps_package_id = dispatched_package_id(
        aps_handoff_dispatch_state,
        dispatched_state=aps_dispatched_state,
        expected_package_kind=aps_package_kind,
    )
    unexpected_kinds = set()
    for package in packages:
        if package.package_kind in allowed_source_kinds:
            continue
        if package.package_kind == aps_package_kind and package.output_package_id == allowed_aps_package_id:
            continue
        unexpected_kinds.add(package.package_kind)
    return sorted(unexpected_kinds)


def canonical_payload_values(
    *,
    values: Any,
    packages: list[L3OutputPackage],
    package_kinds: Iterable[str],
    package_attr: str,
) -> list[str] | None:
    ordered_packages = packages_in_kind_order(packages, package_kinds=package_kinds)
    expected_values = [str(getattr(package, package_attr)) for package in ordered_packages]
    if isinstance(values, list):
        normalized_values = [str(item or "").strip() for item in values]
        if len(normalized_values) == len(ordered_packages) and set(normalized_values) == set(expected_values):
            return expected_values
        return None
    if isinstance(values, dict):
        by_kind = {package.package_kind: str(getattr(package, package_attr)) for package in ordered_packages}
        by_id = {package.output_package_id: str(getattr(package, package_attr)) for package in ordered_packages}
        normalized = {str(key or "").strip(): str(value or "").strip() for key, value in values.items()}
        if normalized == by_kind:
            return expected_values
        if normalized == by_id:
            return expected_values
    return None


def canonical_payload_hashes(
    *,
    payload_hashes: Any,
    packages: list[L3OutputPackage],
) -> list[str] | None:
    return canonical_payload_values(
        values=payload_hashes,
        packages=packages,
        package_kinds=PACKAGE_REVIEW_PREVIEW_CANDIDATE_KINDS,
        package_attr="payload_hash",
    )


def canonical_payload_refs(
    *,
    payload_refs: Any,
    packages: list[L3OutputPackage],
) -> list[str] | None:
    return canonical_payload_values(
        values=payload_refs,
        packages=packages,
        package_kinds=PACKAGE_REVIEW_PREVIEW_CANDIDATE_KINDS,
        package_attr="payload_ref",
    )
