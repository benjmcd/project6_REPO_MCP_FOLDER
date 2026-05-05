from __future__ import annotations

from app.services import layer3_execution_request_contract as contract
from app.services import layer3_workbench


def _legacy_blocked(
    payload: dict[str, object],
    allowed_fields: frozenset[str],
    forbidden_fields: frozenset[str],
) -> list[str]:
    return sorted(
        set(key for key in payload if key not in allowed_fields)
        | set(key for key in forbidden_fields if key in payload)
    )


def test_execution_request_contract_is_shared_without_behavior_change() -> None:
    assert (
        layer3_workbench.ANALYSIS_EXECUTION_START_ALLOWED_FIELDS
        is contract.ANALYSIS_EXECUTION_START_ALLOWED_FIELDS
    )
    assert (
        layer3_workbench.ANALYSIS_EXECUTION_START_FORBIDDEN_FIELDS
        is contract.ANALYSIS_EXECUTION_START_FORBIDDEN_FIELDS
    )
    assert (
        layer3_workbench.EXECUTION_RESULT_STATUS_ALLOWED_FIELDS
        is contract.EXECUTION_RESULT_STATUS_ALLOWED_FIELDS
    )
    assert (
        layer3_workbench.EXECUTION_RESULT_STATUS_FORBIDDEN_FIELDS
        is contract.EXECUTION_RESULT_STATUS_FORBIDDEN_FIELDS
    )
    assert (
        layer3_workbench.EXECUTION_RESULT_REVIEW_ALLOWED_FIELDS
        is contract.EXECUTION_RESULT_REVIEW_ALLOWED_FIELDS
    )
    assert (
        layer3_workbench.EXECUTION_RESULT_REVIEW_FORBIDDEN_FIELDS
        is contract.EXECUTION_RESULT_REVIEW_FORBIDDEN_FIELDS
    )


def test_execution_request_contract_blocks_same_fields_as_legacy_logic() -> None:
    start_payload = {
        "session_id": "session-1",
        "execution_mode": "synchronous_single_pass",
        "run_all": True,
        "unexpected_field": True,
    }
    assert contract.analysis_execution_start_blocked_fields(start_payload) == _legacy_blocked(
        start_payload,
        contract.ANALYSIS_EXECUTION_START_ALLOWED_FIELDS,
        contract.ANALYSIS_EXECUTION_START_FORBIDDEN_FIELDS,
    )

    status_payload = {
        "session_id": "session-1",
        "operator_view_mode": "status_only",
        "result_review": True,
        "unexpected_field": True,
    }
    assert contract.execution_result_status_blocked_fields(status_payload) == _legacy_blocked(
        status_payload,
        contract.EXECUTION_RESULT_STATUS_ALLOWED_FIELDS,
        contract.EXECUTION_RESULT_STATUS_FORBIDDEN_FIELDS,
    )

    review_payload = {
        "session_id": "session-1",
        "operator_decision": "approved",
        "package_review": True,
        "unexpected_field": True,
    }
    assert contract.execution_result_review_blocked_fields(review_payload) == _legacy_blocked(
        review_payload,
        contract.EXECUTION_RESULT_REVIEW_ALLOWED_FIELDS,
        contract.EXECUTION_RESULT_REVIEW_FORBIDDEN_FIELDS,
    )
