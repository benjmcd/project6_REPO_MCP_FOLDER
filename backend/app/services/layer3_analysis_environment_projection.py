from __future__ import annotations

from collections.abc import Iterable
from typing import Any

from app.services.layer3_utils import json_clone


ANALYSIS_ENVIRONMENT_PROJECTION_SCHEMA_ID = "layer3.analysis_environment_projection.v1"
ANALYSIS_ENVIRONMENT_PROJECTION_AUTHORITY_SOURCE = "read_only_session_summary_projection"
SUBLAYER_VISUALIZATION_STATE_SCHEMA_ID = "layer3.sublayer_visualization_state.v1"

_PLANES = ("quantitative", "qualitative", "hybrid")
_PACKAGE_STATES = {
    "package_constructed",
    "package_review_approved",
    "package_review_submit_recorded",
}
_DELIVERY_REF_KEYS = (
    "external_local_export_receipt_id",
    "provider_private_handoff_receipt_id",
    "server_owned_local_outbox_write_receipt_id",
    "external_export_download_record_ref",
    "prepare_record_ref",
    "dispatch_record_ref",
    "submit_record_ref",
)
_RECORDED_STATES = {
    "package_construction": {"package_constructed"},
    "package_review_submit": {"package_review_submit_recorded", "package_review_approved"},
    "handoff_export_prepare": {"handoff_export_prepared"},
    "aps_handoff_dispatch": {"aps_handoff_dispatched"},
    "external_export_download": {"external_export_download_prepared", "external_export_download_delivered"},
    "server_owned_local_outbox_write": {"server_owned_local_outbox_write_recorded"},
    "local_outbox_provider_private_handoff": {"local_outbox_provider_private_handoff_prepared"},
    "external_local_export": {"external_local_export_recorded"},
}


def _as_dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _as_list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def _string_set(values: Iterable[Any]) -> set[str]:
    return {str(value) for value in values if value is not None}


def _state_of(value: dict[str, Any]) -> str | None:
    for key in (
        "external_local_export_state",
        "provider_private_handoff_state",
        "server_owned_local_outbox_write_state",
        "external_export_download_state",
        "handoff_export_prepare_state",
        "aps_handoff_dispatch_state",
        "package_review_submit_state",
        "package_construction_state",
        "state",
    ):
        state = value.get(key)
        if isinstance(state, str) and state:
            return state
    return None


def _has_ref(value: dict[str, Any], ref_keys: Iterable[str]) -> bool:
    return any(bool(value.get(key)) for key in ref_keys)


def _authority_summary(
    value: dict[str, Any],
    *,
    ref_keys: Iterable[str],
    recorded_states: Iterable[str],
) -> dict[str, Any]:
    state = _state_of(value)
    return {
        "state": state,
        "available": bool(value.get("available")),
        "recorded": bool(_has_ref(value, ref_keys) or (state in set(recorded_states))),
        "blocked_reason": value.get("blocked_reason"),
    }


def _plane_readiness(
    *,
    typing_records: list[Any],
    analysis_sets: list[Any],
    pass_runs: list[Any],
) -> list[dict[str, Any]]:
    typing_planes = _string_set(
        _as_dict(record).get("chosen_modality")
        for record in typing_records
    )
    set_planes = _string_set(
        _as_dict(analysis_set).get("analysis_modality")
        for analysis_set in analysis_sets
    )
    pass_set_ids = _string_set(
        _as_dict(pass_run).get("analysis_set_id")
        for pass_run in pass_runs
    )
    output_set_ids = _string_set(
        _as_dict(pass_run).get("analysis_set_id")
        for pass_run in pass_runs
        if _as_dict(pass_run).get("output_payload_available") is True
    )

    readiness: list[dict[str, Any]] = []
    for plane in _PLANES:
        plane_sets = [
            _as_dict(analysis_set)
            for analysis_set in analysis_sets
            if _as_dict(analysis_set).get("analysis_modality") == plane
        ]
        plane_set_ids = _string_set(analysis_set.get("analysis_set_id") for analysis_set in plane_sets)
        if plane_set_ids & output_set_ids:
            state = "output_ready"
        elif plane_set_ids & pass_set_ids:
            state = "execution_selected"
        elif plane in set_planes:
            state = "analysis_set_ready"
        elif plane in typing_planes:
            state = "typed"
        else:
            state = "absent"
        readiness.append(
            {
                "plane": plane,
                "state": state,
                "typing_record_count": sum(
                    1
                    for record in typing_records
                    if _as_dict(record).get("chosen_modality") == plane
                ),
                "analysis_set_count": len(plane_sets),
                "pass_run_count": sum(
                    1
                    for pass_run in pass_runs
                    if _as_dict(pass_run).get("analysis_set_id") in plane_set_ids
                ),
                "output_payload_count": sum(
                    1
                    for pass_run in pass_runs
                    if _as_dict(pass_run).get("analysis_set_id") in plane_set_ids
                    and _as_dict(pass_run).get("output_payload_available") is True
                ),
            }
        )
    return readiness


def _highest_projection_state(
    *,
    material_count: int,
    typing_count: int,
    analysis_set_count: int,
    latest_plan: dict[str, Any] | None,
    output_payload_count: int,
    package_authority: dict[str, dict[str, Any]],
) -> str:
    if package_authority["external_local_export"]["recorded"]:
        return "delivery_ready"
    if package_authority["local_outbox_provider_private_handoff"]["recorded"]:
        return "delivery_ready"
    if package_authority["server_owned_local_outbox_write"]["recorded"]:
        return "delivery_ready"
    if package_authority["external_export_download"]["recorded"]:
        return "export_ready"
    if package_authority["handoff_export_prepare"]["recorded"]:
        return "handoff_ready"
    if package_authority["aps_handoff_dispatch"]["recorded"]:
        return "handoff_ready"
    if (
        package_authority["package_review_submit"]["recorded"]
        or package_authority["package_review_submit"]["state"] in _PACKAGE_STATES
        or package_authority["package_construction"]["recorded"]
        or package_authority["package_construction"]["state"] in _PACKAGE_STATES
    ):
        return "package_ready"
    if output_payload_count:
        return "output_ready"
    if latest_plan:
        return "planned"
    if analysis_set_count:
        return "input_ready"
    if typing_count:
        return "typed"
    if material_count:
        return "structural"
    return "structural"


def analysis_environment_projection(
    *,
    sublayer_visualization: dict[str, Any],
    package_construction: dict[str, Any],
    package_review_submit: dict[str, Any],
    handoff_export_prepare: dict[str, Any],
    aps_handoff_dispatch: dict[str, Any],
    external_export_download: dict[str, Any],
    server_owned_local_outbox_write: dict[str, Any],
    local_outbox_provider_private_handoff: dict[str, Any],
    external_local_export: dict[str, Any],
    current_gate: str,
    downstream_unavailable: Iterable[str],
    authority_rail: dict[str, Any],
) -> dict[str, Any]:
    downstream_blockers = [str(item) for item in downstream_unavailable]
    authority = _as_dict(authority_rail)
    sublayer = _as_dict(sublayer_visualization)
    blocked_reasons: list[str] = []

    if sublayer.get("schema_id") != SUBLAYER_VISUALIZATION_STATE_SCHEMA_ID:
        blocked_reasons.append("sublayer_visualization_missing_or_invalid")
    if sublayer.get("no_side_effects") is not True:
        blocked_reasons.append("sublayer_visualization_not_read_only")
    source_collection_counts_complete = not blocked_reasons

    material_objects = _as_list(sublayer.get("material_objects"))
    typing_records = _as_list(sublayer.get("typing_records"))
    analysis_sets = _as_list(sublayer.get("analysis_sets"))
    pass_runs = _as_list(sublayer.get("pass_runs"))
    latest_plan_value = sublayer.get("latest_plan")
    latest_plan = latest_plan_value if isinstance(latest_plan_value, dict) else None
    sublayer_collections_truncated = sublayer.get("sublayer_collections_truncated") is True
    source_collection_counts_complete = source_collection_counts_complete and not sublayer_collections_truncated
    output_payload_count = sum(
        1 for pass_run in pass_runs if _as_dict(pass_run).get("output_payload_available") is True
    )

    package_authority = {
        "package_construction": _authority_summary(
            _as_dict(package_construction),
            ref_keys=("construction_basis_hash",),
            recorded_states=_RECORDED_STATES["package_construction"],
        ),
        "package_review_submit": _authority_summary(
            _as_dict(package_review_submit),
            ref_keys=("submit_record_ref",),
            recorded_states=_RECORDED_STATES["package_review_submit"],
        ),
        "handoff_export_prepare": _authority_summary(
            _as_dict(handoff_export_prepare),
            ref_keys=("prepare_record_ref",),
            recorded_states=_RECORDED_STATES["handoff_export_prepare"],
        ),
        "aps_handoff_dispatch": _authority_summary(
            _as_dict(aps_handoff_dispatch),
            ref_keys=("dispatch_record_ref",),
            recorded_states=_RECORDED_STATES["aps_handoff_dispatch"],
        ),
        "external_export_download": _authority_summary(
            _as_dict(external_export_download),
            ref_keys=("external_export_download_record_ref",),
            recorded_states=_RECORDED_STATES["external_export_download"],
        ),
        "server_owned_local_outbox_write": _authority_summary(
            _as_dict(server_owned_local_outbox_write),
            ref_keys=("server_owned_local_outbox_write_receipt_id",),
            recorded_states=_RECORDED_STATES["server_owned_local_outbox_write"],
        ),
        "local_outbox_provider_private_handoff": _authority_summary(
            _as_dict(local_outbox_provider_private_handoff),
            ref_keys=("provider_private_handoff_receipt_id",),
            recorded_states=_RECORDED_STATES["local_outbox_provider_private_handoff"],
        ),
        "external_local_export": _authority_summary(
            _as_dict(external_local_export),
            ref_keys=("external_local_export_receipt_id",),
            recorded_states=_RECORDED_STATES["external_local_export"],
        ),
    }
    projection_state = (
        "blocked"
        if blocked_reasons
        else _highest_projection_state(
            material_count=len(material_objects),
            typing_count=len(typing_records),
            analysis_set_count=len(analysis_sets),
            latest_plan=latest_plan,
            output_payload_count=output_payload_count,
            package_authority=package_authority,
        )
    )

    if not blocked_reasons and projection_state == "structural":
        blocked_reasons.append("analysis_environment_inputs_not_ready")

    available_for_downstream_analysis = projection_state in {
        "output_ready",
        "package_ready",
        "handoff_ready",
        "export_ready",
        "delivery_ready",
    }

    return {
        "schema_id": ANALYSIS_ENVIRONMENT_PROJECTION_SCHEMA_ID,
        "authority_source": ANALYSIS_ENVIRONMENT_PROJECTION_AUTHORITY_SOURCE,
        "projection_mode": "read_only_session_summary_projection",
        "current_gate": current_gate,
        "projection_state": projection_state,
        "available_for_downstream_analysis": available_for_downstream_analysis,
        "blocked_reasons": blocked_reasons,
        "source_state": {
            "sublayer_schema_id": sublayer.get("schema_id"),
            "material_object_count": len(material_objects),
            "typing_record_count": len(typing_records),
            "analysis_set_count": len(analysis_sets),
            "pass_run_count": len(pass_runs),
            "output_payload_count": output_payload_count,
            "latest_plan_status": latest_plan.get("plan_status") if latest_plan else None,
            "latest_plan_approved": bool(latest_plan.get("approved")) if latest_plan else False,
            "source_collection_counts_complete": source_collection_counts_complete,
            "sublayer_collections_truncated": sublayer_collections_truncated,
        },
        "plane_readiness": _plane_readiness(
            typing_records=typing_records,
            analysis_sets=analysis_sets,
            pass_runs=pass_runs,
        ),
        "package_authority": package_authority,
        "authority_rail_summary": {
            "persistence_mode": authority.get("persistence_mode"),
            "execution_enabled": bool(authority.get("execution_enabled")),
            "package_review_enabled": bool(authority.get("package_review_enabled")),
        },
        "downstream_unavailable": downstream_blockers,
        "forbidden_runtime_authority": {
            "write_route_enabled": False,
            "package_mutation_enabled": False,
            "source_promotion_enabled": False,
            "connector_dispatch_enabled": False,
            "provider_url_enabled": False,
            "frontend_durable_authority_enabled": False,
        },
        "no_side_effects": True,
        "sublayer_visualization_unchanged": json_clone(sublayer_visualization) == sublayer_visualization,
    }
