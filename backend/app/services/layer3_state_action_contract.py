from __future__ import annotations

from copy import deepcopy
from typing import Any, Iterable


STATE_ACTION_CONTRACT_SCHEMA_ID = "layer3.state_action_contract.v1"

STATE_ACTION_ADMITTED_CAPABILITIES = (
    {
        "capability": "single_aps_doc_qualitative_execution",
        "admitted": True,
        "source_gate": "119_L3_QUAL_APS_EXEC_ENTRY_FREEZE",
        "scope": "exact single APS content document qualitative pass after plan approval and execution selection",
        "owner_service": "backend/app/services/layer3_qual_aps_execution.py",
        "blocked_downstream": [
            "qualitative_package_handoff_export",
            "broad_qualitative_execution",
            "hybrid_execution",
            "rag_vector_retrieval",
        ],
    },
    {
        "capability": "internal_dispatch_record_only",
        "admitted": True,
        "source_gate": "121_CONNECTOR_DISPATCH_ENTRY_FREEZE",
        "scope": "response-safe internal connector dispatch intent record with no external connector invocation or destination write",
        "owner_service": "backend/app/services/layer3_connector_dispatch_entry.py",
        "blocked_downstream": [
            "connector_destination_dispatch",
            "single_named_connector_dispatch",
            "single_named_destination_dispatch",
            "provider_public_url",
            "package_mutation_reconstruction",
            "local_upload_or_directory_source_expansion",
            "broad_qualitative_execution",
            "hybrid_execution",
            "rag_vector_retrieval",
            "full_mockup_activation",
        ],
    },
)

STATE_ACTION_DEFERRED_CAPABILITIES = (
    {
        "capability": "broad_qualitative_execution",
        "admitted": False,
        "reason": "single_aps_doc_qualitative_pass_only",
        "scope": "all qualitative execution outside the exact single APS-document qualitative pass",
    },
    {
        "capability": "hybrid_execution",
        "admitted": False,
        "reason": "requires_later_freeze",
    },
    {
        "capability": "rag_vector_retrieval",
        "admitted": False,
        "reason": "requires_source_breadth_freeze",
    },
    {
        "capability": "local_upload_or_directory_source_expansion",
        "admitted": False,
        "reason": "requires_source_runtime_widening_freeze",
    },
    {
        "capability": "provider_public_url",
        "admitted": False,
        "reason": "requires_later_delivery_boundary_freeze",
    },
    {
        "capability": "connector_destination_dispatch",
        "admitted": False,
        "reason": "requires_later_delivery_boundary_freeze",
    },
    {
        "capability": "package_mutation_reconstruction",
        "admitted": False,
        "reason": "requires_later_package_lifecycle_freeze",
    },
    {
        "capability": "frontend_only_durable_state",
        "admitted": False,
        "reason": "server_authority_required",
    },
    {
        "capability": "hidden_llm_planning",
        "admitted": False,
        "reason": "owner_service_plan_authority_required",
    },
    {
        "capability": "auth_security_hardening",
        "admitted": False,
        "reason": "deferred_by_operator_instruction",
    },
)


def _clone_json(value: Any) -> Any:
    return deepcopy(value)


def _string_list(values: Iterable[Any]) -> list[str]:
    return [str(value) for value in values]


def build_state_action_contract(
    *,
    state_model: dict[str, Any],
    schema_version: int,
    gate_labels: Iterable[str],
    active_gate_labels: Iterable[str],
    unavailable_gate_labels: Iterable[str],
    plan_preview_unavailable_gate_labels: Iterable[str],
    gate_b_decisions: Iterable[str],
    plan_revision_decisions: Iterable[str],
    execution_result_review_decisions: Iterable[str],
    package_review_submit_decisions: Iterable[str],
    handoff_export_prepare_decisions: Iterable[str],
    aps_handoff_dispatch_operator_decision: str,
    external_export_download_operator_decision: str,
    external_export_download_delivery_operator_decision: str,
    connector_dispatch_record_operator_decision: str,
    terminal_pass_statuses: Iterable[str],
) -> dict[str, Any]:
    state_action_matrix = _clone_json(state_model["states"])
    action_ids = sorted(
        {
            str(action)
            for state in state_action_matrix
            for action in state.get("allowed_next_actions", [])
        }
    )
    return {
        "schema_id": STATE_ACTION_CONTRACT_SCHEMA_ID,
        "schema_version": schema_version,
        "scope": "server_authoritative_workbench_states_and_actions",
        "state_model_schema_id": state_model["schema_id"],
        "authority_order": list(state_model["authority_order"]),
        "gate_labels": _string_list(gate_labels),
        "active_gate_labels": _string_list(active_gate_labels),
        "unavailable_gate_labels": _string_list(unavailable_gate_labels),
        "plan_preview_unavailable_gate_labels": _string_list(plan_preview_unavailable_gate_labels),
        "state_count": len(state_action_matrix),
        "states": [str(state["state"]) for state in state_action_matrix],
        "action_ids": action_ids,
        "state_action_matrix": state_action_matrix,
        "decision_sets": {
            "gate_b": list(gate_b_decisions),
            "plan_revision": sorted(plan_revision_decisions),
            "execution_result_review": sorted(execution_result_review_decisions),
            "package_review_submit": sorted(package_review_submit_decisions),
            "handoff_export_prepare": sorted(handoff_export_prepare_decisions),
            "aps_handoff_dispatch": [aps_handoff_dispatch_operator_decision],
            "external_export_download_prepare": [external_export_download_operator_decision],
            "external_export_download_deliver": [external_export_download_delivery_operator_decision],
            "connector_dispatch_record": [connector_dispatch_record_operator_decision],
        },
        "terminal_pass_statuses": sorted(terminal_pass_statuses),
        "admitted_capabilities": _clone_json(STATE_ACTION_ADMITTED_CAPABILITIES),
        "deferred_capabilities": _clone_json(STATE_ACTION_DEFERRED_CAPABILITIES),
    }
