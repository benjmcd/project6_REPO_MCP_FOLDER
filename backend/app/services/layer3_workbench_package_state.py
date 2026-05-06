from __future__ import annotations

from typing import Any, Iterable

from app.models.models import L3OutputPackage
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
from app.services.layer3_utils import json_clone


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
