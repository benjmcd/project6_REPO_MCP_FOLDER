from app.services.layer3_authority_matrix_contract import (
    AUTHORITY_MATRIX_ADMISSION_VOCABULARY,
    AUTHORITY_MATRIX_COLUMNS,
    AUTHORITY_MATRIX_CONTRACT_DEFINITION_ID,
    AUTHORITY_MATRIX_CONTRACT_SCHEMA_ID,
    AUTHORITY_MATRIX_CONTRACT_SCOPE,
    AUTHORITY_MATRIX_FAIL_CLOSED_RESULT,
    build_authority_matrix_contract,
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
