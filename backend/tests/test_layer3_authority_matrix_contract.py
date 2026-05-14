from app.services.layer3_authority_matrix_contract import (
    AUTHORITY_MATRIX_ADMISSION_VOCABULARY,
    AUTHORITY_MATRIX_COLUMNS,
    AUTHORITY_MATRIX_CONTRACT_DEFINITION_ID,
    AUTHORITY_MATRIX_CONTRACT_SCHEMA_ID,
    AUTHORITY_MATRIX_CONTRACT_SCOPE,
    AUTHORITY_MATRIX_EXISTING_ROUTE_RESPONSE_RESULT,
    AUTHORITY_MATRIX_FAIL_CLOSED_RESULT,
    AUTHORITY_MATRIX_READ_ONLY_EXPOSURE_CONTEXT,
    AUTHORITY_MATRIX_READ_ONLY_EXPOSURE_RESULT,
    AUTHORITY_MATRIX_RESPONSE_MODEL_RESULT,
    build_authority_matrix_contract,
    build_exposed_authority_matrix_contract,
)
from app.services.layer3_state_action_contract import STATE_ACTION_CONTRACT_SCHEMA_ID
from app.services.layer3_state_model_contract import STATE_MODEL_SCHEMA_ID


def test_authority_matrix_contract_is_pure_source_contract() -> None:
    contract = build_authority_matrix_contract()

    assert contract["schema_id"] == AUTHORITY_MATRIX_CONTRACT_SCHEMA_ID
    assert contract["schema_version"] == 1
    assert contract["contract_definition_id"] == AUTHORITY_MATRIX_CONTRACT_DEFINITION_ID
    assert contract["scope"] == AUTHORITY_MATRIX_CONTRACT_SCOPE
    assert contract["source_contract_ids"] == [
        STATE_ACTION_CONTRACT_SCHEMA_ID,
        STATE_MODEL_SCHEMA_ID,
    ]
    assert contract["matrix_columns"] == list(AUTHORITY_MATRIX_COLUMNS)
    assert contract["admission_vocabulary"] == list(AUTHORITY_MATRIX_ADMISSION_VOCABULARY)
    assert contract["fail_closed_result"] == AUTHORITY_MATRIX_FAIL_CLOSED_RESULT


def test_authority_matrix_rows_have_required_columns_and_block_runtime_scope() -> None:
    contract = build_authority_matrix_contract()
    rows = {row["row"]: row for row in contract["authority_matrix"]}

    assert set(rows) == {
        "state_action_contract_substrate",
        "state_model_authority_substrate",
        "workbench_exposure_substrate",
        "route_api_posture",
        "response_dto_posture",
        "rendered_review_posture",
        "negative_test_posture",
        "side_effect_policy",
        "auth_security_posture",
    }

    for row in rows.values():
        assert set(contract["matrix_columns"]) <= set(row)

    assert rows["state_action_contract_substrate"]["schema_or_contract_id"] == STATE_ACTION_CONTRACT_SCHEMA_ID
    assert rows["state_model_authority_substrate"]["schema_or_contract_id"] == STATE_MODEL_SCHEMA_ID
    assert rows["route_api_posture"]["admission_result"] == AUTHORITY_MATRIX_FAIL_CLOSED_RESULT
    assert rows["response_dto_posture"]["admission_result"] == AUTHORITY_MATRIX_FAIL_CLOSED_RESULT
    assert rows["rendered_review_posture"]["admission_result"] == AUTHORITY_MATRIX_FAIL_CLOSED_RESULT
    assert rows["auth_security_posture"]["admission_result"] == AUTHORITY_MATRIX_FAIL_CLOSED_RESULT

    blocked_side_effects = set(rows["side_effect_policy"]["blocked_scope"])
    assert {
        "runtime_behavior",
        "connector_provider_behavior",
        "dispatch",
        "package_mutation",
        "source_expansion",
        "rag_vector_behavior",
    } <= blocked_side_effects


def test_authority_matrix_contract_returns_defensive_copies() -> None:
    first = build_authority_matrix_contract()
    first["authority_matrix"][0]["blocked_scope"].append("mutated")

    second = build_authority_matrix_contract()

    assert "mutated" not in second["authority_matrix"][0]["blocked_scope"]


def test_exposed_authority_matrix_contract_marks_read_only_response_exposure() -> None:
    contract = build_exposed_authority_matrix_contract()
    rows = {row["row"]: row for row in contract["authority_matrix"]}

    assert contract["schema_id"] == AUTHORITY_MATRIX_CONTRACT_SCHEMA_ID
    assert contract["exposure_context"] == AUTHORITY_MATRIX_READ_ONLY_EXPOSURE_CONTEXT
    assert AUTHORITY_MATRIX_READ_ONLY_EXPOSURE_RESULT in contract["admission_vocabulary"]
    assert rows["workbench_exposure_substrate"]["admission_result"] == AUTHORITY_MATRIX_READ_ONLY_EXPOSURE_RESULT
    assert rows["workbench_exposure_substrate"]["blocked_scope"] == []
    assert rows["route_api_posture"]["admission_result"] == AUTHORITY_MATRIX_EXISTING_ROUTE_RESPONSE_RESULT
    assert rows["route_api_posture"]["blocked_scope"] == ["separate_authority_matrix_route"]
    assert rows["response_dto_posture"]["admission_result"] == AUTHORITY_MATRIX_RESPONSE_MODEL_RESULT
    assert set(rows["response_dto_posture"]["blocked_scope"]) == {
        "schema_model_migration_change",
        "separate_response_dto_module_change",
    }
    assert rows["side_effect_policy"]["admission_result"] == "admitted_for_contract_definition_only"
    assert "runtime_behavior" in rows["side_effect_policy"]["blocked_scope"]
