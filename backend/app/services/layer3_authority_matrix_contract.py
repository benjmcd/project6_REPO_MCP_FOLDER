from __future__ import annotations

from copy import deepcopy
from typing import Any

from app.services.layer3_state_action_contract import STATE_ACTION_CONTRACT_SCHEMA_ID
from app.services.layer3_state_model_contract import STATE_MODEL_SCHEMA_ID


AUTHORITY_MATRIX_CONTRACT_SCHEMA_ID = "layer3.authority_matrix_contract.v1"
AUTHORITY_MATRIX_CONTRACT_DEFINITION_ID = "layer3_authority_matrix_contract_definition_v1"
AUTHORITY_MATRIX_CONTRACT_SCOPE = "server_authoritative_next_runtime_tranche_authority_matrix"
AUTHORITY_MATRIX_FAIL_CLOSED_RESULT = "blocked_no_runtime_authority"
AUTHORITY_MATRIX_READ_ONLY_EXPOSURE_CONTEXT = "read_only_bootstrap_readiness_response_paths"
AUTHORITY_MATRIX_READ_ONLY_EXPOSURE_RESULT = "admitted_for_read_only_bootstrap_readiness_exposure"
AUTHORITY_MATRIX_EXISTING_ROUTE_RESPONSE_RESULT = "admitted_for_existing_bootstrap_readiness_openapi_schema"
AUTHORITY_MATRIX_RESPONSE_MODEL_RESULT = "admitted_for_bootstrap_readiness_response_model_shape"
AUTHORITY_MATRIX_RENDERED_REVIEW_RESULT = "admitted_for_existing_read_only_rendered_review_panel"
AUTHORITY_MATRIX_SEPARATE_ROUTE_RESULT = "admitted_for_read_only_authority_matrix_route"

AUTHORITY_MATRIX_ADMISSION_VOCABULARY = (
    "admitted_for_contract_definition_only",
    "requires_audit_before_runtime",
    AUTHORITY_MATRIX_FAIL_CLOSED_RESULT,
    "not_applicable_to_selected_tranche",
)

AUTHORITY_MATRIX_COLUMNS = (
    "canonical_owner",
    "schema_or_contract_id",
    "source_authority",
    "admission_result",
    "blocked_scope",
    "tests_required",
    "next_allowed_action",
)

AUTHORITY_MATRIX_ROWS = (
    {
        "row": "state_action_contract_substrate",
        "canonical_owner": "backend/app/services/layer3_state_action_contract.py",
        "schema_or_contract_id": STATE_ACTION_CONTRACT_SCHEMA_ID,
        "source_authority": "existing_state_action_contract_source",
        "admission_result": "admitted_for_contract_definition_only",
        "blocked_scope": [],
        "tests_required": [
            "state_action_contract_schema_id_reference",
            "state_action_contract_deferred_capabilities_remain_blocked",
        ],
        "next_allowed_action": "reuse_as_source_contract_only",
    },
    {
        "row": "state_model_authority_substrate",
        "canonical_owner": "backend/app/services/layer3_state_model_contract.py",
        "schema_or_contract_id": STATE_MODEL_SCHEMA_ID,
        "source_authority": "existing_workbench_state_model_source",
        "admission_result": "admitted_for_contract_definition_only",
        "blocked_scope": [],
        "tests_required": [
            "state_model_schema_id_reference",
            "state_model_authority_order_reference",
        ],
        "next_allowed_action": "reuse_as_source_contract_only",
    },
    {
        "row": "workbench_exposure_substrate",
        "canonical_owner": "backend/app/services/layer3_workbench.py",
        "schema_or_contract_id": "not_exposed_by_selected_slice",
        "source_authority": "future_route_or_workbench_exposure_requires_later_freeze",
        "admission_result": "requires_audit_before_runtime",
        "blocked_scope": ["workbench_response_wiring", "bootstrap_response_wiring", "readiness_response_wiring"],
        "tests_required": ["prove_no_workbench_response_wiring_in_pure_source_pass"],
        "next_allowed_action": "freeze_workbench_exposure_before_wiring",
    },
    {
        "row": "route_api_posture",
        "canonical_owner": "backend/app/api/layer3.py",
        "schema_or_contract_id": "not_exposed_by_selected_slice",
        "source_authority": "route_api_exposure_not_admitted",
        "admission_result": AUTHORITY_MATRIX_FAIL_CLOSED_RESULT,
        "blocked_scope": ["route_api_exposure", "openapi_response_schema"],
        "tests_required": ["prove_no_route_or_openapi_change_in_pure_source_pass"],
        "next_allowed_action": "freeze_route_api_exposure_before_route_work",
    },
    {
        "row": "response_dto_posture",
        "canonical_owner": "backend/app/schemas/layer3.py",
        "schema_or_contract_id": "not_exposed_by_selected_slice",
        "source_authority": "response_dto_change_not_admitted",
        "admission_result": AUTHORITY_MATRIX_FAIL_CLOSED_RESULT,
        "blocked_scope": ["response_dto_change", "schema_shape_change"],
        "tests_required": ["prove_no_dto_or_schema_shape_change_in_pure_source_pass"],
        "next_allowed_action": "freeze_response_dto_before_schema_work",
    },
    {
        "row": "rendered_review_posture",
        "canonical_owner": "frontend/layer3 review surface",
        "schema_or_contract_id": "not_exposed_by_selected_slice",
        "source_authority": "rendered_operator_panel_not_admitted",
        "admission_result": AUTHORITY_MATRIX_FAIL_CLOSED_RESULT,
        "blocked_scope": ["rendered_operator_panel", "frontend_only_durable_authority"],
        "tests_required": ["prove_no_rendered_ui_change_in_pure_source_pass"],
        "next_allowed_action": "freeze_rendered_review_before_ui_work",
    },
    {
        "row": "negative_test_posture",
        "canonical_owner": "backend/tests",
        "schema_or_contract_id": AUTHORITY_MATRIX_CONTRACT_SCHEMA_ID,
        "source_authority": "pure_source_contract_tests_required",
        "admission_result": "admitted_for_contract_definition_only",
        "blocked_scope": ["runtime_admission_without_negative_tests"],
        "tests_required": [
            "authority_matrix_rows_have_all_columns",
            "authority_matrix_blocks_route_dto_ui_runtime_scope",
        ],
        "next_allowed_action": "add_targeted_pure_source_contract_tests",
    },
    {
        "row": "side_effect_policy",
        "canonical_owner": "backend/app/services/layer3_authority_matrix_contract.py",
        "schema_or_contract_id": AUTHORITY_MATRIX_CONTRACT_SCHEMA_ID,
        "source_authority": "pure_source_contract_only",
        "admission_result": "admitted_for_contract_definition_only",
        "blocked_scope": [
            "runtime_behavior",
            "connector_provider_behavior",
            "dispatch",
            "package_mutation",
            "source_expansion",
            "rag_vector_behavior",
        ],
        "tests_required": ["prove_contract_contains_no_runtime_side_effect_admission"],
        "next_allowed_action": "sync_then_select_next_freeze",
    },
    {
        "row": "auth_security_posture",
        "canonical_owner": "later_auth_security_lane",
        "schema_or_contract_id": "not_exposed_by_selected_slice",
        "source_authority": "auth_security_behavior_not_admitted",
        "admission_result": AUTHORITY_MATRIX_FAIL_CLOSED_RESULT,
        "blocked_scope": ["auth_security_behavior"],
        "tests_required": ["prove_auth_security_behavior_remains_deferred"],
        "next_allowed_action": "freeze_auth_security_before_auth_work",
    },
)


def _clone_json(value: Any) -> Any:
    return deepcopy(value)


def build_authority_matrix_contract(*, schema_version: int = 1) -> dict[str, Any]:
    return {
        "schema_id": AUTHORITY_MATRIX_CONTRACT_SCHEMA_ID,
        "schema_version": schema_version,
        "contract_definition_id": AUTHORITY_MATRIX_CONTRACT_DEFINITION_ID,
        "scope": AUTHORITY_MATRIX_CONTRACT_SCOPE,
        "source_contract_ids": [
            STATE_ACTION_CONTRACT_SCHEMA_ID,
            STATE_MODEL_SCHEMA_ID,
        ],
        "matrix_columns": list(AUTHORITY_MATRIX_COLUMNS),
        "admission_vocabulary": list(AUTHORITY_MATRIX_ADMISSION_VOCABULARY),
        "fail_closed_result": AUTHORITY_MATRIX_FAIL_CLOSED_RESULT,
        "authority_matrix": _clone_json(AUTHORITY_MATRIX_ROWS),
        "runtime_preconditions": [
            "explicit_runtime_freeze",
            "current_main_sync",
            "implementation_audit",
            "targeted_tests",
            "pr_review_clearance",
            "post_merge_current_main_sync",
        ],
    }


def build_exposed_authority_matrix_contract(
    *,
    schema_version: int = 1,
    exposure_context: str = AUTHORITY_MATRIX_READ_ONLY_EXPOSURE_CONTEXT,
) -> dict[str, Any]:
    contract = build_authority_matrix_contract(schema_version=schema_version)
    contract["exposure_context"] = exposure_context
    contract["source_contract_variant"] = "exposure_aware_read_only_bootstrap_readiness"
    contract["admission_vocabulary"] = [
        *contract["admission_vocabulary"],
        AUTHORITY_MATRIX_READ_ONLY_EXPOSURE_RESULT,
        AUTHORITY_MATRIX_EXISTING_ROUTE_RESPONSE_RESULT,
        AUTHORITY_MATRIX_RESPONSE_MODEL_RESULT,
        AUTHORITY_MATRIX_RENDERED_REVIEW_RESULT,
        AUTHORITY_MATRIX_SEPARATE_ROUTE_RESULT,
    ]
    rows = {row["row"]: row for row in contract["authority_matrix"]}
    rows["workbench_exposure_substrate"].update(
        {
            "schema_or_contract_id": AUTHORITY_MATRIX_CONTRACT_SCHEMA_ID,
            "source_authority": "existing_workbench_bootstrap_readiness_wiring_admitted_by_429",
            "admission_result": AUTHORITY_MATRIX_READ_ONLY_EXPOSURE_RESULT,
            "blocked_scope": [],
            "tests_required": [
                "prove_bootstrap_readiness_body_includes_authority_matrix_contract",
                "prove_builder_parity_includes_authority_matrix_contract",
            ],
            "next_allowed_action": "sync_exposure_before_next_runtime_freeze",
        }
    )
    rows["route_api_posture"].update(
        {
            "schema_or_contract_id": AUTHORITY_MATRIX_CONTRACT_SCHEMA_ID,
            "source_authority": "separate_read_only_authority_matrix_route_admitted_by_459",
            "admission_result": AUTHORITY_MATRIX_SEPARATE_ROUTE_RESULT,
            "blocked_scope": [],
            "tests_required": [
                "prove_existing_bootstrap_readiness_openapi_schema_includes_authority_matrix_contract",
                "prove_separate_authority_matrix_route_response_schema",
                "prove_separate_authority_matrix_route_reuses_exposed_contract",
                "prove_no_runtime_side_effect_admission",
            ],
            "next_allowed_action": "sync_separate_route_before_next_runtime_freeze",
        }
    )
    rows["response_dto_posture"].update(
        {
            "canonical_owner": "backend/app/api/layer3.py",
            "schema_or_contract_id": AUTHORITY_MATRIX_CONTRACT_SCHEMA_ID,
            "source_authority": "explicit_bootstrap_readiness_response_model_fields_admitted_by_429",
            "admission_result": AUTHORITY_MATRIX_RESPONSE_MODEL_RESULT,
            "blocked_scope": ["schema_model_migration_change", "separate_response_dto_module_change"],
            "tests_required": [
                "prove_bootstrap_readiness_response_models_include_authority_matrix_contract",
                "prove_response_body_contains_exposure_aware_authority_matrix_contract",
            ],
            "next_allowed_action": "sync_exposure_before_schema_or_dto_module_work",
        }
    )
    rows["rendered_review_posture"].update(
        {
            "schema_or_contract_id": AUTHORITY_MATRIX_CONTRACT_SCHEMA_ID,
            "source_authority": "existing_read_only_rendered_review_panel_admitted_by_439_441",
            "admission_result": AUTHORITY_MATRIX_RENDERED_REVIEW_RESULT,
            "blocked_scope": ["frontend_only_durable_authority"],
            "tests_required": [
                "prove_existing_read_only_authority_matrix_review_panel_uses_bootstrap_contract",
                "prove_no_rendered_ui_change_in_source_contract_update",
                "prove_frontend_only_durable_authority_remains_blocked",
            ],
            "next_allowed_action": "sync_rendered_review_posture_before_next_runtime_freeze",
        }
    )
    return contract
